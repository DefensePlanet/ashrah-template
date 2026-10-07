"""
Command handlers — bridge between CLI args and business logic.

Each handler corresponds to a CLI subcommand and follows the pattern:
    handle_<command>(args: argparse.Namespace) -> int (exit code)
"""

import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from .coordinator import SearchCoordinator
from .extractors.structured_data import StructuredDataExtractor
from .models import Category, Gender, Product, UserProfile
from .output import (
    format_telegram,
    output_json,
    output_product,
    output_profile,
    output_stats,
    output_table,
    output_watchlist,
)
from .resolver import resolve_url

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

WARDROBE_DIR = Path.home() / ".wardrobe"
PROFILE_PATH = WARDROBE_DIR / "profile.yaml"
HISTORY_DIR = WARDROBE_DIR / "history"


# ---------------------------------------------------------------------------
# Profile I/O
# ---------------------------------------------------------------------------

def _load_profile() -> UserProfile:
    """Load user profile from ~/.wardrobe/profile.yaml."""
    if not PROFILE_PATH.exists():
        return UserProfile()

    try:
        import yaml
        with open(PROFILE_PATH) as f:
            data = yaml.safe_load(f) or {}
        return UserProfile(
            sizes=data.get("sizes", {}),
            color_strict=data.get("color_strict", False),
            max_price=data.get("max_price"),
            enabled_platforms=data.get("enabled_platforms", [
                "ebay", "poshmark", "depop", "mercari", "thredup", "grailed"
            ]),
        )
    except ImportError:
        # Fall back to JSON-style parsing if PyYAML not available
        logger.warning("PyYAML not available, using default profile")
        return UserProfile()
    except Exception as e:
        logger.warning("Failed to load profile: %s", e)
        return UserProfile()


def _save_profile(profile: UserProfile) -> None:
    """Save user profile to ~/.wardrobe/profile.yaml."""
    WARDROBE_DIR.mkdir(parents=True, exist_ok=True)

    try:
        import yaml
        with open(PROFILE_PATH, "w") as f:
            yaml.dump(profile.to_dict(), f, default_flow_style=False)
    except ImportError:
        # Fall back to JSON
        with open(PROFILE_PATH.with_suffix(".json"), "w") as f:
            json.dump(profile.to_dict(), f, indent=2)
        logger.info("Saved profile as JSON (PyYAML not available)")


def _save_history(product: Product, results: list, duration_ms: int) -> None:
    """Save search to history directory."""
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    now = datetime.now()
    timestamp = now.strftime("%Y%m%d_%H%M%S")
    filename = HISTORY_DIR / f"search_{timestamp}.json"

    record = {
        "timestamp": now.isoformat(),
        "duration_ms": duration_ms,
        "product": product.to_dict(),
        "results_count": len(results),
        "results": [r.to_dict() for r in results[:50]],
    }

    with open(filename, "w") as f:
        json.dump(record, f, indent=2)
    logger.debug("Search history saved to %s", filename)


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------

def handle_search(args) -> int:
    """Handle the 'search' command."""
    url = args.url
    as_json = getattr(args, "json", False)
    as_telegram = getattr(args, "telegram", False)
    limit = getattr(args, "limit", 20)
    dry_run = getattr(args, "dry_run", False)
    max_price = getattr(args, "max_price", None)
    color_strict = getattr(args, "color_strict", False)
    platforms_str = getattr(args, "platforms", None)
    no_expand = getattr(args, "no_expand", False)
    no_vision = getattr(args, "no_vision", False)
    no_resolve = getattr(args, "no_resolve", False)
    gender = getattr(args, "gender", "any")
    size_strict = getattr(args, "size_strict", True) and not getattr(args, "size_fuzzy", False)
    min_score = getattr(args, "min_score", 0)

    # Telegram mode caps results for phone-screen readability
    if as_telegram:
        limit = min(limit, 5)

    platforms = None
    if platforms_str:
        platforms = [p.strip().lower() for p in platforms_str.split(",")]

    # Load profile
    profile = _load_profile()
    if max_price is not None:
        profile.max_price = max_price
    if color_strict:
        profile.color_strict = True

    # Step 1: Resolve indirect URLs (Pinterest pins, short links, etc.)
    if not no_resolve:
        resolved_url, source = resolve_url(url)
        if source != "direct":
            _print_status(f"Resolved {source} link -> {resolved_url}")
            if resolved_url == url and source == "pinterest":
                _print_error(
                    "Could not resolve Pinterest pin to a product page. "
                    "Try copying the product URL directly from the pin's "
                    '"Visit" button.'
                )
                return 1
            url = resolved_url
    else:
        source = "direct"

    # Step 2: Extract product details
    extractor = StructuredDataExtractor()
    if not extractor.can_handle(url):
        _print_error(
            "Cannot extract product from this URL. "
            "Make sure 'extruct' and 'requests' are installed:\n"
            "  pip install extruct requests"
        )
        return 1

    _print_status("Extracting product details...")
    product = extractor.extract(url)
    if not product:
        _print_error("Failed to extract product details from URL")
        return 1

    # Override size from profile if product size is unknown
    if product.size == "Unknown" and profile.sizes:
        profile_size = profile.get_size(product.category)
        if profile_size:
            product.size = profile_size

    # Dry run — just show extracted product
    if dry_run:
        print(output_product(product, as_json))
        if not as_json:
            # Show what platforms would be searched
            coordinator = SearchCoordinator()
            available = coordinator.available_searchers(
                platforms or profile.enabled_platforms
            )
            if available:
                names = [s.name for s in available]
                print(f"  Would search: {', '.join(names)}")
            else:
                print(
                    f"  {_YELLOW}No searchers available. "
                    f"Set EBAY_APP_ID + EBAY_CERT_ID for eBay.{_RESET}"
                )
            print()
        return 0

    # Full search
    features = []
    if not no_expand:
        features.append("query expansion")
    if not no_vision:
        features.append("vision matching")
    feature_str = f" [+{', '.join(features)}]" if features else ""
    _print_status(
        f"Searching for '{product.brand} {product.model}' "
        f"across resale platforms...{feature_str}"
    )
    start = time.time()
    coordinator = SearchCoordinator()
    results = coordinator.search(
        product,
        profile=profile,
        max_results=limit,
        platforms=platforms,
        no_expand=no_expand,
        no_vision=no_vision,
        gender_filter=gender,
        size_strict=size_strict,
    )
    duration_ms = int((time.time() - start) * 1000)

    # Save history
    _save_history(product, results, duration_ms)

    # Output
    platforms_searched = [
        s.name for s in coordinator.available_searchers(
            platforms or profile.enabled_platforms
        )
    ]
    if as_json:
        metadata = {
            "duration_ms": duration_ms,
            "platforms_searched": platforms_searched,
        }
        print(output_json(product, results, metadata))
    elif as_telegram:
        print(format_telegram(product, results, limit, platforms_searched))
    else:
        print(output_table(product, results, limit))
        print(f"  {_DIM}Search completed in {duration_ms}ms{_RESET}")
        print()

    return 0


def handle_config(args) -> int:
    """Handle the 'config' command."""
    as_json = getattr(args, "json", False)
    show = getattr(args, "show", False)

    if show:
        profile = _load_profile()
        print(output_profile(profile.to_dict(), as_json))
        return 0

    # Update profile with provided sizes
    profile = _load_profile()

    changed = False
    for cat_name in ["tops", "bottoms", "shoes", "outerwear", "accessories", "dresses"]:
        val = getattr(args, cat_name, None)
        if val is not None:
            profile.sizes[cat_name] = val
            changed = True

    max_price = getattr(args, "max_price", None)
    if max_price is not None:
        profile.max_price = max_price
        changed = True

    color_strict = getattr(args, "color_strict", None)
    if color_strict is not None:
        profile.color_strict = color_strict
        changed = True

    platforms_str = getattr(args, "platforms", None)
    if platforms_str:
        profile.enabled_platforms = [
            p.strip().lower() for p in platforms_str.split(",")
        ]
        changed = True

    if changed:
        _save_profile(profile)
        _print_success("Profile updated")
        print(output_profile(profile.to_dict(), as_json))
    else:
        _print_error("No changes specified. Use --show to display profile.")
        return 1

    return 0


def handle_test_extractor(args) -> int:
    """Handle the 'test-extractor' command."""
    url = args.url
    as_json = getattr(args, "json", False)
    no_resolve = getattr(args, "no_resolve", False)

    # Resolve indirect URLs before extraction
    if not no_resolve:
        resolved_url, source = resolve_url(url)
        if source != "direct":
            _print_status(f"Resolved {source} link -> {resolved_url}")
            if resolved_url == url and source == "pinterest":
                _print_error(
                    "Could not resolve Pinterest pin to a product page. "
                    "Try copying the product URL directly from the pin's "
                    '"Visit" button.'
                )
                return 1
            url = resolved_url

    extractor = StructuredDataExtractor()
    if not extractor.can_handle(url):
        _print_error(
            "Cannot handle URL. Install dependencies:\n"
            "  pip install extruct requests"
        )
        return 1

    _print_status("Extracting product details...")
    product = extractor.extract(url)

    if product:
        print(output_product(product, as_json))
        return 0
    else:
        _print_error("No product data found at URL")
        return 1


def handle_test_searcher(args) -> int:
    """Handle the 'test-searcher' command."""
    platform = args.platform.lower()
    as_json = getattr(args, "json", False)

    coordinator = SearchCoordinator()
    all_searchers = coordinator.searchers

    # Find the requested searcher
    target = None
    for s in all_searchers:
        if s.name == platform:
            target = s
            break

    if not target:
        known = [s.name for s in all_searchers]
        _print_error(
            f"Unknown platform: {platform}\n"
            f"  Known: {', '.join(known) if known else 'none'}"
        )
        return 1

    # Test availability
    available = target.is_available()
    if as_json:
        print(json.dumps({
            "platform": target.name,
            "available": available,
            "class": target.__class__.__name__,
        }, indent=2))
    else:
        status = f"{_GREEN}available{_RESET}" if available else f"{_RED}unavailable{_RESET}"
        print(f"\n  {target.name}: {status} ({target.__class__.__name__})")
        if not available:
            if target.name == "ebay":
                print(
                    f"  {_DIM}Set EBAY_APP_ID and EBAY_CERT_ID "
                    f"environment variables{_RESET}"
                )
        print()

    return 0


def handle_history(args) -> int:
    """Handle the 'history' command."""
    limit = getattr(args, "limit", 10)
    as_json = getattr(args, "json", False)

    if not HISTORY_DIR.exists():
        if as_json:
            print(json.dumps({"history": [], "total": 0}))
        else:
            print(f"\n  {_DIM}No search history found.{_RESET}\n")
        return 0

    # List history files sorted by name (timestamp-based)
    files = sorted(HISTORY_DIR.glob("search_*.json"), reverse=True)
    files = files[:limit]

    if as_json:
        history = []
        for f in files:
            try:
                with open(f) as fh:
                    history.append(json.load(fh))
            except (json.JSONDecodeError, IOError):
                continue
        print(json.dumps({"history": history, "total": len(history)}, indent=2))
        return 0

    if not files:
        print(f"\n  {_DIM}No search history found.{_RESET}\n")
        return 0

    print(f"\n  {_BOLD}Recent Searches{_RESET}")
    print(f"  {'─' * 60}")
    for f in files:
        try:
            with open(f) as fh:
                record = json.load(fh)
            product = record.get("product", {})
            ts = record.get("timestamp", "?")
            count = record.get("results_count", 0)
            brand = product.get("brand", "?")
            model = product.get("model", "?")
            price = product.get("retail_price", 0)

            print(
                f"  {_DIM}{ts}{_RESET}  "
                f"{brand} {model}  "
                f"${price:.2f}  "
                f"{count} results"
            )
        except (json.JSONDecodeError, IOError, KeyError):
            continue

    print(f"  {'─' * 60}")
    print(f"  {_DIM}Showing {len(files)} most recent{_RESET}\n")
    return 0


def handle_watch(args) -> int:
    """Handle the 'watch' subcommand.

    Supports four modes:
    - watch <url>       Add a product to the watchlist
    - watch --list      Show all watched items
    - watch --remove ID Remove a watch by ID
    - watch --check     Run one check cycle for all watches
    """
    from . import watcher

    as_json = getattr(args, "json", False)

    # List mode
    if getattr(args, "list", False):
        watches = watcher.list_watches()
        print(output_watchlist(watches, as_json=as_json))
        return 0

    # Remove mode
    remove_id = getattr(args, "remove", None)
    if remove_id:
        success = watcher.remove_watch(remove_id)
        if success:
            _print_success(f"Removed watch: {remove_id}")
        else:
            _print_error(f"Watch not found: {remove_id}")
            return 1
        return 0

    # Check mode
    if getattr(args, "check", False):
        verbose = getattr(args, "verbose", False)
        _print_status("Running watch check cycle...")
        results = watcher.check_watches(verbose=verbose)
        _print_success(
            f"Checked {results['checked']} items, "
            f"{results['notifications']} notifications sent, "
            f"{results['errors']} errors"
        )
        return 0

    # Add mode (requires URL)
    url = getattr(args, "url", None)
    if not url:
        _print_error(
            "Provide a URL to watch, or use --list, --remove, --check.\n"
            "  Usage: wardrobe_finder watch <url> [--name NAME] [--max-price N]"
        )
        return 1

    no_resolve = getattr(args, "no_resolve", False)

    # Resolve indirect URLs
    if not no_resolve:
        resolved_url, source = resolve_url(url)
        if source != "direct":
            _print_status(f"Resolved {source} link -> {resolved_url}")
            if resolved_url == url and source == "pinterest":
                _print_error(
                    "Could not resolve Pinterest pin to a product page. "
                    "Try copying the product URL directly from the pin's "
                    '"Visit" button.'
                )
                return 1
            url = resolved_url

    # Extract product details
    extractor = StructuredDataExtractor()
    if not extractor.can_handle(url):
        _print_error(
            "Cannot extract product from this URL. "
            "Make sure 'extruct' and 'requests' are installed:\n"
            "  pip install extruct requests"
        )
        return 1

    _print_status("Extracting product details...")
    product = extractor.extract(url)
    if not product:
        _print_error("Failed to extract product details from URL")
        return 1

    # Override size from profile if needed
    profile = _load_profile()
    if product.size == "Unknown" and profile.sizes:
        profile_size = profile.get_size(product.category)
        if profile_size:
            product.size = profile_size

    name = getattr(args, "name", None) or f"{product.brand} {product.model}"
    max_price = getattr(args, "max_price", None)
    platforms_str = getattr(args, "platforms", None)
    platforms = None
    if platforms_str:
        platforms = [p.strip().lower() for p in platforms_str.split(",")]

    watch_id = watcher.add_watch(
        url=url,
        name=name,
        max_price=max_price,
        platforms=platforms,
        product=product,
    )
    _print_success(f"Watching: {name} (id: {watch_id})")
    print(output_product(product, as_json))
    return 0


def handle_stats(args) -> int:
    """Handle the 'stats' subcommand."""
    as_json = getattr(args, "json", False)
    stats = _compute_stats()
    print(output_stats(stats, as_json=as_json))
    return 0


def _compute_stats() -> dict:
    """Aggregate statistics from search history and watchlist."""
    from . import watcher
    from collections import Counter

    stats: dict = {
        "total_searches": 0,
        "total_results": 0,
        "avg_results_per_search": 0.0,
        "avg_duration_ms": 0.0,
        "watch_count": 0,
        "total_checks": 0,
        "top_brands": [],
        "platform_results": {},
    }

    # -- History stats --
    brand_counter: Counter = Counter()
    platform_counter: Counter = Counter()
    total_duration = 0

    if HISTORY_DIR.exists():
        history_files = sorted(HISTORY_DIR.glob("search_*.json"))
        stats["total_searches"] = len(history_files)

        for f in history_files:
            try:
                with open(f) as fh:
                    record = json.load(fh)

                results_count = record.get("results_count", 0)
                stats["total_results"] += results_count
                total_duration += record.get("duration_ms", 0)

                product = record.get("product", {})
                brand = product.get("brand", "Unknown")
                if brand and brand != "Unknown":
                    brand_counter[brand] += 1

                for r in record.get("results", []):
                    platform = r.get("platform", "unknown")
                    platform_counter[platform] += 1

            except (json.JSONDecodeError, IOError):
                continue

        if stats["total_searches"] > 0:
            stats["avg_results_per_search"] = (
                stats["total_results"] / stats["total_searches"]
            )
            stats["avg_duration_ms"] = (
                total_duration / stats["total_searches"]
            )

    stats["top_brands"] = brand_counter.most_common(10)
    stats["platform_results"] = dict(platform_counter)

    # -- Watch stats --
    watches = watcher.list_watches()
    stats["watch_count"] = len(watches)
    stats["total_checks"] = sum(w.check_count for w in watches)

    return stats


# ---------------------------------------------------------------------------
# Print helpers
# ---------------------------------------------------------------------------

_GREEN = "\033[92m"
_RED = "\033[91m"
_YELLOW = "\033[93m"
_BOLD = "\033[1m"
_DIM = "\033[2m"
_RESET = "\033[0m"

if not sys.stdout.isatty():
    _GREEN = _RED = _YELLOW = _BOLD = _DIM = _RESET = ""


def _print_status(msg: str) -> None:
    print(f"  {_DIM}{msg}{_RESET}", file=sys.stderr)


def _print_success(msg: str) -> None:
    print(f"  {_GREEN}{msg}{_RESET}", file=sys.stderr)


def _print_error(msg: str) -> None:
    print(f"  {_RED}Error: {msg}{_RESET}", file=sys.stderr)
