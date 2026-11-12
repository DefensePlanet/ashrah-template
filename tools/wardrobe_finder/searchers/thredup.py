"""
ThredUp marketplace searcher using Playwright with stealth.

Scrapes ThredUp search results for secondhand clothing listings.
ThredUp is a curated secondhand marketplace with quality-checked items
and structured data on listing cards (size, condition, brand).
Uses headless Chromium with anti-detection measures.

ThredUp DOM structure (verified 2026-02):
  - Grid items:  div.grid-item[data-item-number]
  - Card body:   div.item-card-body
  - Brand:       h3.heading-xs-serif (inside anchor to brand page)
  - Size + Type: div.body-copy children (e.g. "Size 10" | "Cargo Pants")
  - Price:       strong.body-copy-bold (e.g. "$19.99")
  - Product link: a[href*="/product/"]
  - Image:       img inside div.item-card-image

Note: ThredUp search via direct URL is unreliable (returns errors or
Cloudflare blocks). The scraper uses homepage search-box navigation
for more reliable results.
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

_BASE_URL = "https://www.thredup.com"
_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)
_PAGE_LOAD_TIMEOUT = 20_000  # ms (ThredUp can be slow)
_SELECTOR_TIMEOUT = 10_000   # ms
_MIN_DELAY = 0.5             # seconds
_MAX_DELAY = 2.0             # seconds


def _log(msg: str) -> None:
    """Log to stderr for debugging."""
    print(f"[thredup] {msg}", file=sys.stderr)


def _random_delay(lo: float = _MIN_DELAY, hi: float = _MAX_DELAY) -> None:
    """Sleep a random interval to mimic human behavior."""
    time.sleep(random.uniform(lo, hi))


def _parse_price(text: str) -> Optional[float]:
    """Extract a numeric price from text like '$12.99' or '$1,200'."""
    if not text:
        return None
    match = re.search(r"\$[\s]*([\d,]+(?:\.\d{1,2})?)", text)
    if match:
        return float(match.group(1).replace(",", ""))
    return None


class ThredUpSearcher(SearcherBase if isinstance(SearcherBase, type) else object):
    """Scrapes ThredUp search results via headless Playwright."""

    name: str = "thredup"

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def search(self, product, max_results: int = 20) -> list:
        """Search ThredUp for *product*, return up to *max_results* items."""
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
        _log(f"Searching for: {query}")

        pw = None
        browser = None
        try:
            pw = sync_playwright().start()
            browser, context = self._launch_browser(pw)
            page = context.new_page()

            # Navigate to homepage first (direct search URLs are flaky) -
            page.goto(
                _BASE_URL, wait_until="domcontentloaded",
                timeout=_PAGE_LOAD_TIMEOUT,
            )
            _random_delay(1.5, 3.0)

            # Detect Cloudflare bot challenge ----------------------------
            if self._is_blocked(page):
                _log("Cloudflare bot detection triggered -- cannot proceed")
                return []

            # Dismiss cookie/consent banners if present -----------------
            self._dismiss_banner(page)

            # Use the search box to navigate to results -----------------
            search_input = None
            for sel in [
                'input[type="search"]',
                'input[placeholder*="earch"]',
                'input[name="search"]',
            ]:
                try:
                    inp = page.locator(sel).first
                    if inp.is_visible(timeout=2000):
                        search_input = inp
                        break
                except Exception:
                    continue

            if not search_input:
                _log("Could not find search input on homepage")
                return []

            search_input.fill(query)
            _random_delay(0.5, 1.0)
            search_input.press("Enter")
            _random_delay(3.0, 5.0)

            # Detect bot block after search -----------------------------
            if self._is_blocked(page):
                _log("Cloudflare bot detection triggered after search")
                return []

            # Dismiss any post-search popups ----------------------------
            self._dismiss_banner(page)

            # Wait for product grid to appear ---------------------------
            card_selectors = [
                '.grid-item',
                '[data-item-number]',
                'a[href*="/product/"]',
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
                _log("No product cards found -- page may be empty or blocked")
                return []

            _random_delay(0.5, 1.0)

            # Scroll to trigger lazy-loaded images ----------------------
            self._gentle_scroll(page, scrolls=3)

            # Extract listings via JS (using verified selectors) --------
            raw_listings = page.evaluate(
                """
                () => {
                    // ThredUp grid items have data-item-number attribute
                    const items = document.querySelectorAll('.grid-item[data-item-number]');
                    const results = [];

                    for (const item of items) {
                        // Product link
                        const link = item.querySelector('a[href*="/product/"]');
                        const href = link ? link.getAttribute('href') : '';
                        if (!href) continue;

                        // Card body contains structured text
                        const body = item.querySelector('.item-card-body');
                        if (!body) continue;

                        // Brand: h3 heading
                        const brandEl = body.querySelector('h3');
                        const brand = brandEl ? brandEl.textContent.trim() : '';

                        // Size and type: body-copy divs
                        let size = '';
                        let itemType = '';
                        const bodyCopyDivs = body.querySelectorAll('div.body-copy');
                        for (const div of bodyCopyDivs) {
                            const txt = div.textContent.trim();
                            if (txt.startsWith('Size ')) {
                                size = txt;
                            } else if (txt.length > 0 && txt.length < 60 && !txt.startsWith('$')) {
                                itemType = txt;
                            }
                        }

                        // Price: strong element
                        const priceEl = body.querySelector('strong');
                        const price = priceEl ? priceEl.textContent.trim() : '';

                        // Discount price: look for second price
                        let origPrice = '';
                        const allPriceEls = body.querySelectorAll('strong, s, [class*="strike"]');
                        for (const el of allPriceEls) {
                            const txt = el.textContent.trim();
                            if (txt.startsWith('$') && txt !== price) {
                                origPrice = txt;
                                break;
                            }
                        }

                        // Image
                        const imgEl = item.querySelector('.item-card-image img');
                        const imgSrc = imgEl
                            ? (imgEl.getAttribute('src') || '')
                            : '';
                        const imgAlt = imgEl
                            ? (imgEl.getAttribute('alt') || '')
                            : '';

                        results.push({
                            href: href,
                            brand: brand,
                            item_type: itemType,
                            title: imgAlt,
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
            # ThredUp promo modal / email signup
            "[data-testid='modal-close']",
            "[data-testid='close-button']",
            "button[aria-label='close']",
            "button[aria-label='Close']",
            "button[aria-label='Close dialog']",
            "[class*='ModalClose']",
            "[class*='modal-close']",
            # Email signup popup
            "button:has-text('No thanks')",
            "button:has-text('No Thanks')",
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

        # Build full URL (strip query tracking params)
        clean_href = href.split("?")[0] if "?" in href else href
        listing_url = (
            clean_href
            if clean_href.startswith("http")
            else f"{_BASE_URL}{clean_href}"
        )

        # Title -- combine brand + item type; fall back to img alt
        brand = item.get("brand", "").strip()
        item_type = item.get("item_type", "").strip()
        alt_title = item.get("title", "").strip()

        if brand and item_type:
            title = f"{brand} {item_type}"
        elif alt_title:
            title = alt_title
        elif brand:
            title = brand
        else:
            return None

        # Price -- prefer the first (current/sale) price
        price = _parse_price(item.get("price", ""))
        if price is None:
            price = _parse_price(item.get("orig_price", ""))
        if price is None:
            return None

        # Size -- strip "Size " prefix (e.g. "Size 10" -> "10")
        size_text = item.get("size", "")
        size = re.sub(r"^Size[\s:]*", "", size_text, flags=re.IGNORECASE).strip()

        # Color -- extract from title text
        color = self._extract_color(title)

        # Condition -- ThredUp shows condition on some cards
        condition = self._parse_condition(title)

        # Thumbnail
        thumbnail = item.get("img_src", "") or None

        return SearchResult(
            platform="thredup",
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
        """Parse condition with ThredUp-specific terms.

        ThredUp uses standardized conditions: "Like New", "Excellent",
        "Very Good", "Good", "Fair".
        """
        if not text:
            return Condition.UNKNOWN if Condition else "Unknown"
        text_lower = text.lower()
        # ThredUp-specific condition labels
        if "like new" in text_lower:
            return Condition.LIKE_NEW if Condition else "Like New"
        if "excellent" in text_lower:
            return Condition.LIKE_NEW if Condition else "Like New"
        if "very good" in text_lower:
            return Condition.GOOD if Condition else "Good"
        # Fall through to the shared parser
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
