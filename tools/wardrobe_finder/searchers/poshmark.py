"""
Poshmark marketplace searcher using Playwright with stealth.

Scrapes Poshmark search results for secondhand clothing listings.
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

_BASE_URL = "https://poshmark.com"
_SEARCH_URL = (
    "{base}/search?query={query}&department=All&type=listings&src=dir"
)
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
    print(f"[poshmark] {msg}", file=sys.stderr)


def _random_delay(lo: float = _MIN_DELAY, hi: float = _MAX_DELAY) -> None:
    """Sleep a random interval to mimic human behavior."""
    time.sleep(random.uniform(lo, hi))


def _parse_price(text: str) -> Optional[float]:
    """Extract a numeric price from text like '$55' or '$1,200'."""
    if not text:
        return None
    match = re.search(r"\$[\s]*([\d,]+(?:\.\d{1,2})?)", text)
    if match:
        return float(match.group(1).replace(",", ""))
    return None


class PoshmarkSearcher(SearcherBase if isinstance(SearcherBase, type) else object):
    """Scrapes Poshmark search results via headless Playwright."""

    name: str = "poshmark"

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def search(self, product, max_results: int = 20) -> list:
        """Search Poshmark for *product*, return up to *max_results* items."""
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

            # Wait for listing cards to appear --------------------------
            try:
                page.wait_for_selector(
                    ".card.card--small", timeout=_SELECTOR_TIMEOUT
                )
            except Exception:
                _log("No listing cards found — page may be empty or blocked")
                return []

            _random_delay(0.5, 1.0)

            # Scroll down to trigger lazy-loaded images -----------------
            self._gentle_scroll(page, scrolls=3)

            # Extract listings via JS -----------------------------------
            raw_listings = page.evaluate(
                """
                () => {
                    const cards = document.querySelectorAll('.card.card--small');
                    const results = [];
                    for (const card of cards) {
                        const link = card.querySelector('a[href*="/listing/"]');
                        if (!link) continue;

                        const titleEl = card.querySelector('.tile__title');
                        const priceEl = card.querySelector('.fw--bold');
                        const origPriceEl = card.querySelector('.td--lt');
                        const sizeEl = card.querySelector('.tile__details__pipe__size');
                        const brandEl = card.querySelector('.tile__details__pipe__brand');
                        const imgEl = card.querySelector('img[src*="cloudfront"]')
                                    || card.querySelector('img[alt]');

                        results.push({
                            href: link.getAttribute('href') || '',
                            title: titleEl ? titleEl.textContent.trim() : '',
                            price: priceEl ? priceEl.textContent.trim() : '',
                            orig_price: origPriceEl ? origPriceEl.textContent.trim() : '',
                            size: sizeEl ? sizeEl.textContent.trim() : '',
                            brand: brandEl ? brandEl.textContent.trim() : '',
                            img_src: imgEl
                                ? (imgEl.getAttribute('src') || imgEl.getAttribute('data-src') || '')
                                : '',
                            img_alt: imgEl ? (imgEl.getAttribute('alt') || '') : '',
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
            # Cookie consent
            "button:has-text('Accept')",
            "button:has-text('Got it')",
            "button:has-text('OK')",
            # Poshmark promo modal
            "[data-test='modal-close']",
            ".modal__close-btn",
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

        # Title — prefer the dedicated title element, fall back to img alt
        title = item.get("title", "") or item.get("img_alt", "")
        if not title:
            return None

        # Price — prefer the bold (current) price
        price = _parse_price(item.get("price", ""))
        if price is None:
            price = _parse_price(item.get("orig_price", ""))
        if price is None:
            return None

        # Size — strip the "Size: " prefix
        size_text = item.get("size", "")
        size = re.sub(r"^Size:\s*", "", size_text, flags=re.IGNORECASE).strip()

        # Color — Poshmark doesn't show color on the card; try to
        # extract from title text
        color = self._extract_color(title)

        # Condition — parse from title text with Poshmark-specific terms
        condition = self._parse_condition_poshmark(title)

        # Thumbnail
        thumbnail = item.get("img_src", "") or None

        return SearchResult(
            platform="poshmark",
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
    def _parse_condition_poshmark(text: str):
        """Parse condition with Poshmark-specific abbreviations.

        Extends the shared parse_condition with marketplace jargon:
        EUC = Excellent Used Condition, GUC = Good Used Condition.
        """
        if not text:
            return Condition.UNKNOWN if Condition else "Unknown"
        text_lower = text.lower()
        # Poshmark-specific abbreviations (check first)
        if "euc" in text_lower:
            return Condition.LIKE_NEW if Condition else "Like New"
        if "guc" in text_lower:
            return Condition.GOOD if Condition else "Good"
        # Fall through to the shared parser
        if parse_condition:
            return parse_condition(text)
        return Condition.UNKNOWN if Condition else "Unknown"

    @staticmethod
    def _extract_color(text: str) -> str:
        """Best-effort color extraction from listing title."""
        # Common color keywords (ordered long -> short to prefer specific
        # matches like "Light Blue" over "Blue")
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
