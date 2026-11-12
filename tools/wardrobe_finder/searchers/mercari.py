"""
Mercari marketplace searcher using Playwright with stealth.

Scrapes Mercari search results for secondhand clothing listings.
Uses headless Chromium with anti-detection measures for reliable
personal-use scraping.

Mercari DOM structure (verified 2026-02):
  - Search URL: /search/?keyword={query} (direct URL works sometimes)
  - Mercari uses aggressive Cloudflare bot detection that may block
    headless browsers. When blocked, the scraper returns empty gracefully.
  - Item links: a[href*="/item/"]
  - Title: img alt or text elements within card
  - Price: spans/divs with "$" prefix
  - Cards: various data-testid and class patterns (React-rendered)

Note: Mercari has aggressive Cloudflare protection. The scraper attempts
direct URL first, then falls back to homepage search-box navigation.
When both fail due to bot detection, returns empty list gracefully.
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

_BASE_URL = "https://www.mercari.com"
_SEARCH_URL = "{base}/search/?keyword={query}"
_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)
_PAGE_LOAD_TIMEOUT = 20_000  # ms
_SELECTOR_TIMEOUT = 10_000   # ms
_MIN_DELAY = 0.5             # seconds
_MAX_DELAY = 2.0             # seconds


def _log(msg: str) -> None:
    """Log to stderr for debugging."""
    print(f"[mercari] {msg}", file=sys.stderr)


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


class MercariSearcher(SearcherBase if isinstance(SearcherBase, type) else object):
    """Scrapes Mercari search results via headless Playwright."""

    name: str = "mercari"

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def search(self, product, max_results: int = 20) -> list:
        """Search Mercari for *product*, return up to *max_results* items."""
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

            # Try direct search URL first --------------------------------
            page.goto(url, wait_until="domcontentloaded", timeout=_PAGE_LOAD_TIMEOUT)
            _random_delay(2.0, 4.0)

            # Detect Cloudflare bot challenge ----------------------------
            if self._is_blocked(page):
                _log("Cloudflare bot detection on direct URL -- trying homepage search")
                # Fallback: navigate to homepage and use search box
                page.goto(
                    _BASE_URL,
                    wait_until="domcontentloaded",
                    timeout=_PAGE_LOAD_TIMEOUT,
                )
                _random_delay(2.0, 3.0)

                if self._is_blocked(page):
                    _log("Cloudflare bot detection on homepage -- cannot proceed")
                    return []

                # Dismiss banners and use search box
                self._dismiss_banner(page)
                if not self._search_via_input(page, query):
                    return []
                _random_delay(3.0, 5.0)

                if self._is_blocked(page):
                    _log("Cloudflare triggered after search -- cannot proceed")
                    return []

            # Dismiss cookie/consent banners if present -----------------
            self._dismiss_banner(page)

            # Wait for item links to appear -----------------------------
            # NOTE: Must wait for item links BEFORE checking "0 results"
            # because Mercari's React app renders the results count
            # via JS after the initial DOM load. Checking body text
            # too early gives false "0 results" before items render.
            try:
                page.wait_for_selector(
                    'a[href*="/item/"]', timeout=_SELECTOR_TIMEOUT
                )
            except Exception:
                # No item links found — check if the page says "0 results"
                body_text = page.evaluate(
                    "document.body.innerText.substring(0, 1000)"
                )
                if "0 results" in body_text or "No results found" in body_text:
                    _log("No results for this query on Mercari")
                else:
                    _log("No item links found -- page may be empty or blocked")
                return []

            _random_delay(0.5, 1.0)

            # Scroll to trigger lazy-loaded images ----------------------
            self._gentle_scroll(page, scrolls=3)

            # Extract listings via JS -----------------------------------
            raw_listings = page.evaluate(
                """
                () => {
                    // Find all links to item pages and deduplicate
                    const links = document.querySelectorAll('a[href*="/item/"]');
                    const seen = new Set();
                    const results = [];

                    for (const link of links) {
                        const href = link.getAttribute('href') || '';
                        if (!href || seen.has(href)) continue;
                        seen.add(href);

                        // Walk up to find the card container
                        const card = link.closest('[data-testid*="Item"]')
                                  || link.closest('[data-testid*="item"]')
                                  || link.parentElement
                                  || link;

                        // Price: look for first $ text in card
                        let price = '';
                        const allEls = card.querySelectorAll('span, p, div');
                        for (const el of allEls) {
                            const txt = el.textContent.trim();
                            if (txt.startsWith('$') && txt.length < 15) {
                                price = txt;
                                break;
                            }
                        }

                        // Title: img alt text (most reliable on Mercari)
                        const img = card.querySelector('img') || link.querySelector('img');
                        let title = '';
                        let imgSrc = '';
                        if (img) {
                            title = img.getAttribute('alt') || '';
                            imgSrc = img.getAttribute('src') || img.getAttribute('data-src') || '';
                        }

                        // Fallback title: data-testid="ItemName" or text elements
                        if (!title) {
                            const nameEl = card.querySelector('[data-testid*="ItemName"]')
                                        || card.querySelector('[data-testid*="itemName"]');
                            if (nameEl) title = nameEl.textContent.trim();
                        }

                        if (!title || !price) continue;

                        results.push({
                            href: href,
                            title: title,
                            price: price,
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

    @staticmethod
    def _search_via_input(page, query: str) -> bool:
        """Try to search by typing into the search box on the page."""
        for sel in [
            'input[type="search"]',
            'input[placeholder*="earch"]',
            'input[name="keyword"]',
            'input[aria-label*="earch"]',
        ]:
            try:
                inp = page.locator(sel).first
                if inp.is_visible(timeout=2000):
                    inp.fill(query)
                    _random_delay(0.5, 1.0)
                    inp.press("Enter")
                    return True
            except Exception:
                continue
        _log("Could not find search input on page")
        return False

    def _dismiss_banner(self, page) -> None:
        """Try to dismiss cookie consent or promotional overlays."""
        dismiss_selectors = [
            # Cookie consent (Mercari uses "Got it" for cookie banner)
            "button:has-text('Got it')",
            "button:has-text('Accept')",
            "button:has-text('Accept All')",
            "button:has-text('OK')",
            # Mercari app download prompts / modals
            "[data-testid='close-button']",
            "button[aria-label='close']",
            "button[aria-label='Close']",
            "[class*='ModalClose']",
            "[class*='modal'] button[class*='close']",
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

        # Title
        title = item.get("title", "")
        if not title:
            return None

        # Price
        price = _parse_price(item.get("price", ""))
        if price is None:
            return None

        # Size -- Mercari rarely shows size on the card; leave empty
        size = item.get("size", "").strip()

        # Color -- extract from title text
        color = self._extract_color(title)

        # Condition -- parse from title text
        condition = self._parse_condition(title)

        # Thumbnail
        thumbnail = item.get("img_src", "") or None

        return SearchResult(
            platform="mercari",
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
