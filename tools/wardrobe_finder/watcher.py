"""
Core watch logic for persistent monitoring.

Manages the watchlist (add/remove/list), runs check cycles that search
resale marketplaces for each watched item, diffs against previously seen
results, and fires Telegram notifications for new matches and price drops.

Storage layout under ~/.wardrobe/:
    watchlist.json              All WatchEntry records
    watch-state/<id>.json       Per-item seen-results state
"""

import json
import logging
import os
import re
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .coordinator import SearchCoordinator
from .models import Category, Product, SearchResult, UserProfile, WatchEntry
from .notifier import send_telegram_message

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

WARDROBE_DIR = Path.home() / ".wardrobe"
WATCHLIST_PATH = WARDROBE_DIR / "watchlist.json"
WATCH_STATE_DIR = WARDROBE_DIR / "watch-state"


# ---------------------------------------------------------------------------
# Watchlist I/O (atomic writes)
# ---------------------------------------------------------------------------

def _load_watchlist() -> List[WatchEntry]:
    """Load all watch entries from watchlist.json."""
    if not WATCHLIST_PATH.exists():
        return []
    try:
        with open(WATCHLIST_PATH) as f:
            data = json.load(f)
        entries = []
        for item in data:
            entries.append(WatchEntry(**item))
        return entries
    except (json.JSONDecodeError, IOError, TypeError) as e:
        logger.error("Failed to load watchlist: %s", e)
        return []


def _save_watchlist(entries: List[WatchEntry]) -> None:
    """Atomically write watchlist to disk (write-to-temp, then rename)."""
    WARDROBE_DIR.mkdir(parents=True, exist_ok=True)
    tmp_fd, tmp_path = tempfile.mkstemp(
        dir=WARDROBE_DIR, prefix=".watchlist-", suffix=".tmp"
    )
    try:
        with os.fdopen(tmp_fd, "w") as f:
            json.dump([e.to_dict() for e in entries], f, indent=2)
        os.replace(tmp_path, WATCHLIST_PATH)
    except Exception:
        # Clean up temp file on failure
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


# ---------------------------------------------------------------------------
# Per-item state I/O
# ---------------------------------------------------------------------------

def _load_watch_state(watch_id: str) -> dict:
    """Load seen-results state for a watch ID.

    State format:
        {
            "seen": {
                "<url>": {"price": float, "first_seen": str}
            }
        }
    """
    state_path = WATCH_STATE_DIR / f"{watch_id}.json"
    if not state_path.exists():
        return {"seen": {}}
    try:
        with open(state_path) as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        logger.warning("Failed to load state for %s: %s", watch_id, e)
        return {"seen": {}}


def _save_watch_state(watch_id: str, state: dict) -> None:
    """Atomically write watch state to disk."""
    WATCH_STATE_DIR.mkdir(parents=True, exist_ok=True)
    state_path = WATCH_STATE_DIR / f"{watch_id}.json"
    tmp_fd, tmp_path = tempfile.mkstemp(
        dir=WATCH_STATE_DIR, prefix=f".{watch_id}-", suffix=".tmp"
    )
    try:
        with os.fdopen(tmp_fd, "w") as f:
            json.dump(state, f, indent=2)
        os.replace(tmp_path, state_path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


# ---------------------------------------------------------------------------
# ID generation
# ---------------------------------------------------------------------------

def _generate_id(product: dict) -> str:
    """Create a URL-safe slug from brand + model + size.

    Example: "Nike Air Force 1 '07" size 10.5 -> "nike-air-force-1-07-10.5"
    """
    brand = product.get("brand", "unknown")
    model = product.get("model", "unknown")
    size = product.get("size", "")

    raw = f"{brand} {model}"
    if size and size.lower() != "unknown":
        raw += f" {size}"

    # Lowercase, strip non-alphanumeric (keep dots for sizes), collapse dashes
    slug = raw.lower()
    slug = re.sub(r"[^a-z0-9.\s-]", "", slug)
    slug = re.sub(r"[\s]+", "-", slug)
    slug = re.sub(r"-{2,}", "-", slug)
    slug = slug.strip("-")
    return slug or "watch"


# ---------------------------------------------------------------------------
# Diffing
# ---------------------------------------------------------------------------

def _diff_results(
    current_results: List[SearchResult],
    seen_state: dict,
) -> Tuple[List[SearchResult], List[Dict]]:
    """Compare current results against previously seen state.

    Returns:
        (new_matches, price_drops)
        - new_matches: SearchResult objects with URLs not previously seen
        - price_drops: dicts with keys url, title, platform, old_price,
          new_price, pct for listings whose price decreased
    """
    seen = seen_state.get("seen", {})
    new_matches: List[SearchResult] = []
    price_drops: List[Dict] = []

    for result in current_results:
        url = result.url
        if url not in seen:
            new_matches.append(result)
        else:
            old_price = seen[url].get("price", 0)
            if old_price > 0 and result.price < old_price:
                drop_pct = ((old_price - result.price) / old_price) * 100
                price_drops.append({
                    "url": url,
                    "title": result.title,
                    "platform": result.platform,
                    "old_price": old_price,
                    "new_price": result.price,
                    "pct": drop_pct,
                })

    return new_matches, price_drops


# ---------------------------------------------------------------------------
# Product reconstruction
# ---------------------------------------------------------------------------

def _reconstruct_product(product_dict: dict) -> Product:
    """Rebuild a Product dataclass from a stored dict snapshot."""
    cat_value = product_dict.get("category", "unknown")
    try:
        category = Category(cat_value)
    except ValueError:
        category = Category.UNKNOWN

    return Product(
        brand=product_dict.get("brand", "Unknown"),
        model=product_dict.get("model", "Unknown"),
        size=product_dict.get("size", "Unknown"),
        color=product_dict.get("color", "Unknown"),
        retail_price=product_dict.get("retail_price", 0.0),
        url=product_dict.get("url", ""),
        category=category,
        image_url=product_dict.get("image_url"),
        description=product_dict.get("description"),
        sku=product_dict.get("sku"),
        upc=product_dict.get("upc"),
        mpn=product_dict.get("mpn"),
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def add_watch(
    url: str,
    name: str,
    max_price: Optional[float],
    platforms: Optional[List[str]],
    product: Product,
) -> str:
    """Add a product to the watchlist.

    Returns the generated watch ID.
    """
    product_dict = product.to_dict()
    watch_id = _generate_id(product_dict)

    # Deduplicate: if this ID already exists, remove the old one
    entries = _load_watchlist()
    entries = [e for e in entries if e.id != watch_id]

    entry = WatchEntry(
        id=watch_id,
        name=name,
        url=url,
        product=product_dict,
        max_price=max_price,
        platforms=platforms,
        added=datetime.now().isoformat(),
    )
    entries.append(entry)
    _save_watchlist(entries)
    logger.info("Added watch: %s (%s)", name, watch_id)
    return watch_id


def remove_watch(watch_id: str) -> bool:
    """Remove a watch by ID. Returns True if found and removed."""
    entries = _load_watchlist()
    before = len(entries)
    entries = [e for e in entries if e.id != watch_id]

    if len(entries) == before:
        return False

    _save_watchlist(entries)

    # Clean up state file
    state_path = WATCH_STATE_DIR / f"{watch_id}.json"
    if state_path.exists():
        try:
            state_path.unlink()
        except OSError:
            pass

    logger.info("Removed watch: %s", watch_id)
    return True


def list_watches() -> List[WatchEntry]:
    """Return all watch entries."""
    return _load_watchlist()


def check_watches(verbose: bool = False) -> Dict:
    """Run one check cycle for all watched items.

    For each watch:
    1. Reconstruct the Product from stored dict
    2. Run SearchCoordinator.search()
    3. Diff against seen state
    4. Send Telegram notifications for new/price-drop matches
    5. Update state and watchlist metadata

    Returns a summary dict with counts.
    """
    entries = _load_watchlist()
    if not entries:
        logger.info("Watchlist is empty, nothing to check")
        return {"checked": 0, "notifications": 0, "errors": 0}

    # Load profile for default platforms/sizes
    from .handlers import _load_profile
    profile = _load_profile()

    coordinator = SearchCoordinator()
    total_notifications = 0
    total_errors = 0

    for entry in entries:
        try:
            if verbose:
                logger.warning("Checking: %s (%s)", entry.name, entry.id)

            product = _reconstruct_product(entry.product)

            # Override size from profile if unknown
            if product.size == "Unknown" and profile.sizes:
                profile_size = profile.get_size(product.category)
                if profile_size:
                    product.size = profile_size

            # Build a search profile with per-watch overrides
            search_profile = UserProfile(
                sizes=profile.sizes,
                color_strict=profile.color_strict,
                max_price=entry.max_price or profile.max_price,
                enabled_platforms=entry.platforms or profile.enabled_platforms,
            )

            # Run search (no expand/vision for speed in batch checks)
            results = coordinator.search(
                product,
                profile=search_profile,
                max_results=30,
                platforms=entry.platforms,
                no_expand=True,
                no_vision=True,
            )

            # Filter by max_price if set
            if entry.max_price is not None:
                results = [
                    r for r in results if r.price <= entry.max_price
                ]

            # Diff against seen state
            state = _load_watch_state(entry.id)
            new_matches, price_drops = _diff_results(results, state)

            # Cap notifications per item
            new_matches = new_matches[:3]
            price_drops = price_drops[:3]

            # Send notification if there are new finds
            if new_matches or price_drops:
                from .output import format_watch_notification
                msg = format_watch_notification(
                    entry.name, new_matches, price_drops, entry.product,
                )
                sent = send_telegram_message(msg)
                if sent:
                    total_notifications += 1
                    if verbose:
                        logger.warning(
                            "  Notified: %d new, %d price drops",
                            len(new_matches), len(price_drops),
                        )
                else:
                    logger.warning(
                        "Failed to send notification for %s", entry.name
                    )
            elif verbose:
                logger.warning("  No new matches for %s", entry.name)

            # Update seen state with ALL current results
            now_iso = datetime.now().isoformat()
            seen = state.get("seen", {})
            for r in results:
                if r.url not in seen:
                    seen[r.url] = {
                        "price": r.price,
                        "first_seen": now_iso,
                    }
                else:
                    seen[r.url]["price"] = r.price
            state["seen"] = seen
            _save_watch_state(entry.id, state)

            # Update watchlist metadata
            entry.last_checked = now_iso
            entry.check_count += 1

        except Exception as e:
            logger.error("Error checking %s: %s", entry.name, e)
            total_errors += 1

    # Persist updated metadata (last_checked, check_count)
    _save_watchlist(entries)

    summary = {
        "checked": len(entries),
        "notifications": total_notifications,
        "errors": total_errors,
    }
    logger.info(
        "Check cycle complete: %d checked, %d notifications, %d errors",
        summary["checked"], summary["notifications"], summary["errors"],
    )
    return summary
