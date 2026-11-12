"""
Grailed marketplace searcher using Playwright with stealth.

Scrapes Grailed search results for secondhand men's fashion listings.
Grailed is a curated marketplace focused on men's designer and
streetwear clothing. Uses headless Chromium with anti-detection measures.

Grailed DOM structure (verified 2026-02):
  - Feed items: div[class*="feedItem"] (UserItemForFeed_feedItem__*)
  - Designer:   div[class*="UserItem_designer__"]
  - Title:      div[class*="UserItem_title__"]
  - Size:       div[class*="UserItem_size__"]
  - Price:      span[data-testid="Current"]
  - Orig price: span[data-testid="Original"]
  - Link:       a[href*="/listings/"] inside the feed item
  - Image:      img inside UserItem_listingCoverPhoto__
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

_BASE_URL = "https://www.grailed.com"
_SEARCH_URL = "{base}/shop?query={query}"
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
    print(f"[grailed] {msg}", file=sys.stderr)


def _random_delay(lo: float = _MIN_DELAY, hi: float = _MAX_DELAY) -> None:
    """Sleep a random interval to mimic human behavior."""
    time.sleep(random.uniform(lo, hi))


def _parse_price(text: str) -> Optional[float]:
    """Extract a numeric price from text like '$55' or '$1,200.50'."""
    if not text:
        return None
    match = re.search(r"\$[\s]*([\d,]+(?:\.\d{1,2})?)", text)
    if match:
        return float(match.group(1).replace(",", ""))
    return None


class GrailedSearcher(SearcherBase if isinstance(SearcherBase, type) else object):
    """Scrapes Grailed search results via headless Playwright."""

    name: str = "grailed"

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def search(self, product, max_results: int = 20) -> list:
        """Search Grailed for *product*, return up to *max_results* items."""
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

            # Detect Cloudflare bot challenge ----------------------------
            if self._is_blocked(page):
                _log("Cloudflare bot detection triggered -- cannot proceed")
                return []

            # Dismiss cookie/consent banners if present -----------------
            self._dismiss_banner(page)

            # Wait for feed items to appear (verified selectors) --------
            card_selectors = [
                '[class*="feedItem"]',
                '[class*="UserItem_root"]',
                'a[href*="/listings/"]',
            ]
            found_selector = None
            for sel in card_selectors:
                try:
                    page.wait_for_selector(sel, timeout=_SELECTOR_TIMEOUT)
                    found_selector = sel
                    break
                except Exception:
                    continue

            if not found_selector:
                _log("No listing cards found -- page may be empty or blocked")
                return []

            _random_delay(0.5, 1.0)

            # Scroll to trigger lazy-loaded images ----------------------
            self._gentle_scroll(page, scrolls=3)

            # Extract listings via JS (using verified selectors) --------
            raw_listings = page.evaluate(
                """
                () => {
                    // Grailed feed items are divs with "feedItem" in class
                    const items = document.querySelectorAll('[class*="feedItem"]');
                    const results = [];

                    for (const item of items) {
                        const link = item.querySelector('a[href*="/listings/"]');
                        if (!link) continue;
                        const href = link.getAttribute('href') || '';
                        if (!href) continue;

                        // Designer: div with "UserItem_designer" in class
                        const designerEl = item.querySelector('[class*="UserItem_designer"]');
                        const designer = designerEl ? designerEl.textContent.trim() : '';

                        // Title: div with "UserItem_title" in class
                        const titleEl = item.querySelector('[class*="UserItem_title"]');
                        const title = titleEl ? titleEl.textContent.trim() : '';

                        // Size: div with "UserItem_size" in class
                        const sizeEl = item.querySelector('[class*="UserItem_size"]');
                        const size = sizeEl ? sizeEl.textContent.trim() : '';

                        // Price: span[data-testid="Current"]
                        const priceEl = item.querySelector('[data-testid="Current"]');
                        const price = priceEl ? priceEl.textContent.trim() : '';

                        // Original price: span[data-testid="Original"]
                        const origPriceEl = item.querySelector('[data-testid="Original"]');
                        const origPrice = origPriceEl ? origPriceEl.textContent.trim() : '';

                        // Image: img inside the cover photo container
                        const imgEl = item.querySelector('[class*="listingCoverPhoto"] img')
                                   || item.querySelector('img');
                        const imgSrc = imgEl
                            ? (imgEl.getAttribute('src') || '')
                            : '';
                        const imgAlt = imgEl
                            ? (imgEl.getAttribute('alt') || '')
                            : '';

                        results.push({
                            href: href,
                            designer: designer,
                            title: title || imgAlt,
                            price: price,
                            orig_price: origPrice,
                            size: size,
                            img_src: imgSrc,
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

    @staticmethod
    def _is_blocked(page) -> bool:
        """Detect Cloudflare or other bot challenges."""
        try:
            text = page.evaluate("document.body.innerText.substring(0, 500)")
            blocked_signals = [
                "Performing security verification",
                "Verify you are human",
                "Ray ID:",
                "Access Denied",
            ]
            return any(s in text for s in blocked_signals)
        except Exception:
            return False

    def _dismiss_banner(self, page) -> None:
        """Try to dismiss cookie consent or promotional overlays."""
        dismiss_selectors = [
            # Cookie consent
            "button:has-text('Accept')",
            "button:has-text('Accept All')",
            "button:has-text('Got it')",
            "button:has-text('OK')",
            # Grailed modals / signup prompts
            "[data-testid='close-button']",
            "button[aria-label='close']",
            "button[aria-label='Close']",
            "[class*='ModalClose']",
            "[class*='modal-close']",
            "button:has-text('No thanks')",
            "button:has-text('Maybe later')",
            # App download banner
            "[class*='AppBanner'] button",
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

        # Strip Grailed tracking params from href
        clean_href = href.split("?")[0] if "?" in href else href

        # Build full URL
        listing_url = (
            clean_href
            if clean_href.startswith("http")
            else f"{_BASE_URL}{clean_href}"
        )

        # Title -- combine designer + title for Grailed listings
        designer = item.get("designer", "").strip()
        title_raw = item.get("title", "").strip()
        if designer and title_raw:
            title = f"{designer} - {title_raw}"
        elif designer:
            title = designer
        elif title_raw:
            title = title_raw
        else:
            return None

        # Price -- prefer the current (potentially discounted) price
        price = _parse_price(item.get("price", ""))
        if price is None:
            price = _parse_price(item.get("orig_price", ""))
        if price is None:
            return None

        # Size
        size = item.get("size", "").strip()

        # Color -- extract from title text
        color = self._extract_color(title)

        # Condition -- parse from title text (Grailed condition
        # typically only appears in listing detail, not on the card)
        condition = self._parse_condition(title)

        # Thumbnail
        thumbnail = item.get("img_src", "") or None

        return SearchResult(
            platform="grailed",
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
    def _parse_condition(text: str):
        """Parse condition from title text using keyword matching."""
        if not text:
            return Condition.UNKNOWN if Condition else "Unknown"
        if parse_condition:
            return parse_condition(text)
        return Condition.UNKNOWN if Condition else "Unknown"

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
