"""
Depop marketplace searcher using Playwright with stealth.

Scrapes Depop search results for secondhand clothing listings.
Uses headless Chromium with anti-detection measures for reliable
personal-use scraping.
"""

import re
import sys
import time
import random
from typing import List, Optional
from urllib.parse import quote_plus

try:
    from .base import SearcherBase
    from ..models import Product, SearchResult, Condition, parse_condition
except ImportError:
    # Allow standalone syntax checking / testing
    SearcherBase = object  # type: ignore
    Product = None  # type: ignore
    SearchResult = None  # type: ignore
    Condition = None  # type: ignore
    parse_condition = None  # type: ignore


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_BASE_URL = "https://www.depop.com"
_SEARCH_URL = "{base}/search/?q={query}"
_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)
_PAGE_LOAD_TIMEOUT = 15_000  # ms
_SELECTOR_TIMEOUT = 10_000   # ms
_MIN_DELAY = 0.5             # seconds
_MAX_DELAY = 2.0             # seconds


def _log(msg: str) -> None:
    """Log to stderr for debugging."""
    print(f"[depop] {msg}", file=sys.stderr)


def _random_delay(lo: float = _MIN_DELAY, hi: float = _MAX_DELAY) -> None:
    """Sleep a random interval to mimic human behavior."""
    time.sleep(random.uniform(lo, hi))


def _parse_price(text: str) -> Optional[float]:
    """Extract a numeric price from text like '$20.00' or '$1,200.50'."""
    if not text:
        return None
    match = re.search(r"\$[\s]*([\d,]+(?:\.\d{1,2})?)", text)
    if match:
        return float(match.group(1).replace(",", ""))
    return None


def _slug_to_title(slug: str) -> str:
    """Convert a Depop product URL slug into a readable title.

    Example: "elianna_23-nike-air-force-1-white-2968" -> "Nike Air Force 1 White"
    """
    if not slug:
        return ""
    # Strip the seller prefix (everything before the first '-')
    # Depop slugs: /products/{seller}-{description}-{id}/
    parts = slug.strip("/").split("/")
    last = parts[-1] if parts else slug
    # Remove trailing numeric id (e.g. "-2968")
    last = re.sub(r"-[a-f0-9]{4}$", "", last)
    # Remove seller prefix: everything up to and including the first hyphen
    # after a username (usernames can contain underscores, not hyphens)
    # Pattern: seller_name-actual-title-words
    dash_idx = last.find("-")
    if dash_idx > 0:
        last = last[dash_idx + 1:]
    # Replace hyphens with spaces, title-case
    title = last.replace("-", " ").strip()
    # Title-case each word
    title = " ".join(w.capitalize() for w in title.split())
    return title


class DepopSearcher(SearcherBase if isinstance(SearcherBase, type) else object):
    """Scrapes Depop search results via headless Playwright."""

    name: str = "depop"

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def search(self, product, max_results: int = 20) -> list:
        """Search Depop for *product*, return up to *max_results* items."""
        try:
            return self._run_search(product, max_results)
        except Exception as exc:
            _log(f"Search failed: {exc}")
            return []

    def is_available(self) -> bool:
        """Return True if Playwright + Chromium are installed."""
        try:
            from playwright.sync_api import sync_playwright  # noqa: F401
            return True
        except ImportError:
            return False

    # ------------------------------------------------------------------
    # Internal implementation
    # ------------------------------------------------------------------

    def _run_search(self, product, max_results: int) -> list:
        from playwright.sync_api import sync_playwright

        query = product.search_query()
        url = _SEARCH_URL.format(base=_BASE_URL, query=quote_plus(query))
        _log(f"Searching: {url}")

        pw = None
        browser = None
        try:
            pw = sync_playwright().start()
            browser, context = self._launch_browser(pw)
            page = context.new_page()

            # Navigate --------------------------------------------------
            page.goto(url, wait_until="domcontentloaded", timeout=_PAGE_LOAD_TIMEOUT)
            _random_delay(1.5, 3.0)

            # Dismiss cookie banner if present --------------------------
            self._dismiss_banner(page)

            # Wait for product cards to appear --------------------------
            try:
                page.wait_for_selector(
                    '[class*="styles_productCardRoot"]',
                    timeout=_SELECTOR_TIMEOUT,
                )
            except Exception:
                _log("No product cards found — page may be empty or blocked")
                return []

            _random_delay(0.5, 1.0)

            # Scroll to trigger lazy-loaded images ----------------------
            self._gentle_scroll(page, scrolls=3)

            # Extract listings via JS -----------------------------------
            raw_listings = page.evaluate(
                """
                () => {
                    const cards = document.querySelectorAll('[class*="styles_productCardRoot"]');
                    const results = [];
                    for (const card of cards) {
                        const link = card.querySelector('a[href*="/products/"]');
                        if (!link) continue;

                        // Price: prefer discounted price, fall back to regular
                        const discountedEl = card.querySelector('[aria-label="Discounted price"]');
                        const regularEl = card.querySelector('[aria-label="Price"]');
                        const fullPriceEl = card.querySelector('[aria-label="Full price"]');

                        // Size: element with sizeAttributeText class
                        const sizeEl = card.querySelector('[class*="sizeAttributeText"]');

                        // Brand: the last <p> without price or size classes
                        const allP = card.querySelectorAll('[class*="productAttributes"] p');
                        let brand = '';
                        for (const p of allP) {
                            const cls = p.className || '';
                            if (!cls.includes('price') && !cls.includes('size') && !cls.includes('discount')) {
                                brand = p.textContent.trim();
                            }
                        }

                        // Image: main product image
                        const imgEl = card.querySelector('img[class*="mainImage"]')
                                    || card.querySelector('img[loading]');

                        results.push({
                            href: link.getAttribute('href') || '',
                            price: discountedEl
                                ? discountedEl.textContent.trim()
                                : (regularEl ? regularEl.textContent.trim() : ''),
                            full_price: fullPriceEl ? fullPriceEl.textContent.trim() : '',
                            size: sizeEl ? sizeEl.textContent.trim() : '',
                            brand: brand,
                            img_src: imgEl ? (imgEl.getAttribute('src') || '') : '',
                        });
                    }
                    return results;
                }
                """
            )

            _log(f"Found {len(raw_listings)} raw listings")

            # Convert to SearchResult objects ---------------------------
            results = []
            for item in raw_listings:
                result = self._parse_listing(item)
                if result is not None:
                    results.append(result)
                if len(results) >= max_results:
                    break

            _log(f"Returning {len(results)} parsed results")
            return results

        finally:
            if browser:
                try:
                    browser.close()
                except Exception:
                    pass
            if pw:
                try:
                    pw.stop()
                except Exception:
                    pass

    # ------------------------------------------------------------------
    # Browser setup
    # ------------------------------------------------------------------

    def _launch_browser(self, pw):
        """Launch a stealth headless Chromium browser."""
        from playwright_stealth import Stealth

        stealth = Stealth(
            navigator_platform_override="MacIntel",
            navigator_user_agent_override=_USER_AGENT,
            navigator_vendor_override="Google Inc.",
        )

        browser = pw.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
            ],
        )
        context = browser.new_context(
            user_agent=_USER_AGENT,
            viewport={"width": 1920, "height": 1080},
            locale="en-US",
            timezone_id="America/New_York",
            color_scheme="light",
        )
        stealth.apply_stealth_sync(context)

        return browser, context

    # ------------------------------------------------------------------
    # Page interaction helpers
    # ------------------------------------------------------------------

    def _dismiss_banner(self, page) -> None:
        """Try to dismiss cookie consent or promotional overlays."""
        dismiss_selectors = [
            # Cookie consent (Depop uses OneTrust-style banners)
            "button:has-text('Accept')",
            "button:has-text('Accept All')",
            "button:has-text('Accept all cookies')",
            "button:has-text('Got it')",
            "#onetrust-accept-btn-handler",
            "[data-testid='cookieBanner__acceptAllButton']",
            # Generic close
            "button[aria-label='close']",
            "button[aria-label='Close']",
        ]
        for sel in dismiss_selectors:
            try:
                btn = page.locator(sel).first
                if btn.is_visible(timeout=500):
                    btn.click(timeout=1000)
                    _random_delay(0.3, 0.6)
            except Exception:
                pass

    def _gentle_scroll(self, page, scrolls: int = 3) -> None:
        """Scroll down incrementally to trigger lazy loading."""
        for i in range(scrolls):
            page.evaluate(
                f"window.scrollBy(0, {300 + random.randint(100, 400)})"
            )
            _random_delay(0.4, 0.8)

    # ------------------------------------------------------------------
    # Data parsing
    # ------------------------------------------------------------------

    def _parse_listing(self, item: dict):
        """Convert a raw JS-extracted dict into a SearchResult."""
        href = item.get("href", "")
        if not href:
            return None

        # Build full URL
        listing_url = href if href.startswith("http") else f"{_BASE_URL}{href}"

        # Title — Depop cards don't show titles, derive from URL slug
        slug = href.rstrip("/").split("/")[-1] if href else ""
        title = _slug_to_title(slug)
        if not title:
            return None

        # Price
        price = _parse_price(item.get("price", ""))
        if price is None:
            price = _parse_price(item.get("full_price", ""))
        if price is None:
            return None

        # Size — Depop shows "US 8", "US 8.5", "S", "M", "L", etc.
        size = item.get("size", "").strip()

        # Color — Depop doesn't show color on the search card;
        # try to extract from the slug-derived title
        color = self._extract_color(title)

        # Condition — not shown on Depop search cards, always UNKNOWN
        # (would require visiting each listing page to determine)
        condition = Condition.UNKNOWN if Condition else "Unknown"

        # Thumbnail
        thumbnail = item.get("img_src", "") or None

        return SearchResult(
            platform="depop",
            title=title,
            price=price,
            size=size,
            color=color,
            condition=condition,
            url=listing_url,
            thumbnail=thumbnail,
            match_score=0,
        )

    @staticmethod
    def _extract_color(text: str) -> str:
        """Best-effort color extraction from listing title."""
        colors = [
            "Triple White", "Triple Black", "Sail White",
            "University Red", "University Blue", "Royal Blue",
            "Light Blue", "Dark Blue", "Navy Blue",
            "Light Pink", "Hot Pink", "Light Green",
            "Dark Green", "Olive Green", "Forest Green",
            "Light Grey", "Light Gray", "Dark Grey", "Dark Gray",
            "Smoke Grey", "Smoke Gray", "Cool Grey", "Cool Gray",
            "Wolf Grey", "Wolf Gray",
            "White", "Black", "Red", "Blue", "Green", "Pink",
            "Grey", "Gray", "Purple", "Orange", "Yellow", "Brown",
            "Tan", "Beige", "Navy", "Teal", "Maroon", "Cream",
            "Gold", "Silver", "Olive", "Burgundy", "Coral",
            "Khaki", "Wheat", "Flax",
        ]
        text_lower = text.lower()
        for color in colors:
            if color.lower() in text_lower:
                return color
        return "Unknown"
