"""
Structured data extractor — JSON-LD + OpenGraph via extruct library.

Extracts product information from retail URLs by parsing:
1. JSON-LD schema.org/Product structured data (highest quality)
2. OpenGraph meta tags (fallback)
3. Basic HTML meta tags (last resort)
"""

import logging
import re
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from .base import ExtractorBase
from ..models import Product, Category, Gender

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Category detection keywords
# ---------------------------------------------------------------------------

_CATEGORY_KEYWORDS = {
    Category.SHOES: [
        "shoe", "shoes", "sneaker", "sneakers", "boot", "boots",
        "sandal", "sandals", "loafer", "loafers", "slipper",
        "trainer", "trainers", "footwear",
    ],
    Category.TOPS: [
        "shirt", "t-shirt", "tee", "polo", "blouse", "tank",
        "sweater", "hoodie", "sweatshirt", "top", "jersey",
        "henley", "button-down", "cardigan", "pullover",
    ],
    Category.BOTTOMS: [
        "pants", "jeans", "shorts", "trousers", "chinos",
        "joggers", "sweatpants", "leggings", "skirt",
    ],
    Category.OUTERWEAR: [
        "jacket", "coat", "parka", "vest", "windbreaker",
        "anorak", "bomber", "puffer", "down jacket", "fleece",
        "raincoat", "trench",
    ],
    Category.DRESSES: [
        "dress", "gown", "romper", "jumpsuit",
    ],
    Category.ACCESSORIES: [
        "hat", "cap", "beanie", "scarf", "belt", "tie",
        "wallet", "bag", "backpack", "watch", "sunglasses",
        "gloves", "socks",
    ],
}

# Common color words for extraction
_COLOR_WORDS = [
    "black", "white", "red", "blue", "green", "yellow", "orange",
    "purple", "pink", "brown", "grey", "gray", "navy", "cream",
    "beige", "tan", "khaki", "olive", "burgundy", "maroon",
    "teal", "coral", "gold", "silver", "charcoal", "ivory",
    "sage", "rust", "indigo", "lavender", "mint", "slate",
    "forest", "rose", "plum", "wine", "sand", "bone",
    "chocolate", "espresso", "camel", "cognac", "stone",
    "oatmeal", "heather", "denim",
]

# Size patterns
_SIZE_LETTER_RE = re.compile(
    r"\b(XXS|XS|XXXL|XXL|XL|[SML])\b", re.IGNORECASE
)
_SIZE_SHOE_RE = re.compile(
    r"(?:size|sz|us)\s*(\d{1,2}(?:\.\d)?)", re.IGNORECASE
)
# Fallback shoe size: standalone number in valid shoe-size range (6-15, half sizes)
_SIZE_SHOE_STANDALONE_RE = re.compile(
    r"\b(\d{1,2}(?:\.\d)?)\b"
)
_SIZE_WAIST_RE = re.compile(r"\b(\d{2})\s*[xX]\s*(\d{2})\b")
_SIZE_NUMERIC_RE = re.compile(r"\bsize\s+(\d{1,2})\b", re.IGNORECASE)


class StructuredDataExtractor(ExtractorBase):
    """Extract product data from JSON-LD and OpenGraph structured data."""

    name = "structured_data"

    def __init__(self):
        self._extruct_available = None
        self._requests_available = None

    def _check_extruct(self) -> bool:
        """Check if extruct is importable."""
        if self._extruct_available is None:
            try:
                import extruct  # noqa: F401
                self._extruct_available = True
            except ImportError:
                self._extruct_available = False
        return self._extruct_available

    def _check_requests(self) -> bool:
        """Check if requests is importable."""
        if self._requests_available is None:
            try:
                import requests  # noqa: F401
                self._requests_available = True
            except ImportError:
                self._requests_available = False
        return self._requests_available

    def can_handle(self, url: str) -> bool:
        """Can handle any HTTP(S) URL if dependencies are available."""
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False
        return self._check_extruct() and self._check_requests()

    def extract(self, url: str) -> Optional[Product]:
        """Extract product data from a retail URL.

        Fallback chain:
        1. Static HTML (requests + extruct) — fast, no browser overhead
        2. JS-rendered HTML (Playwright + extruct) — for SPAs like Abercrombie
        """
        # Fast path: static HTML
        product = self._extract_static(url)
        if product:
            return product

        # Slow path: JS-rendered (Playwright)
        product = self._extract_rendered(url)
        if product:
            return product

        logger.warning("No structured product data found at %s", url)
        return None

    def _extract_static(self, url: str) -> Optional[Product]:
        """Extract product data from static HTML via requests + extruct."""
        if not self._check_extruct() or not self._check_requests():
            logger.warning(
                "Missing dependencies: pip install extruct requests"
            )
            return None

        import extruct
        import requests

        try:
            resp = requests.get(
                url,
                timeout=15,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/131.0.0.0 Safari/537.36"
                    ),
                    "Accept": "text/html,application/xhtml+xml",
                    "Accept-Language": "en-US,en;q=0.9",
                },
            )
            resp.raise_for_status()
        except requests.RequestException as e:
            logger.error("Failed to fetch URL %s: %s", url, e)
            return None

        return self._extract_from_html(resp.text, url)

    def _extract_rendered(self, url: str) -> Optional[Product]:
        """Extract product data from JS-rendered HTML via Playwright.

        Falls back gracefully if Playwright is not installed.
        Uses stealth settings consistent with the scrapers.
        """
        if not self._check_extruct():
            return None

        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            logger.debug(
                "Playwright not installed, skipping JS-rendered fallback. "
                "Install with: pip install playwright && playwright install chromium"
            )
            return None

        logger.info("Static extraction found no product data, trying Playwright render...")

        pw = None
        browser = None
        try:
            pw = sync_playwright().start()
            browser = pw.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                ],
            )
            context = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/131.0.0.0 Safari/537.36"
                ),
                viewport={"width": 1920, "height": 1080},
                locale="en-US",
                timezone_id="America/New_York",
                color_scheme="light",
            )

            # Apply stealth if available
            try:
                from playwright_stealth import Stealth
                stealth = Stealth(
                    navigator_platform_override="MacIntel",
                    navigator_user_agent_override=(
                        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/131.0.0.0 Safari/537.36"
                    ),
                    navigator_vendor_override="Google Inc.",
                )
                stealth.apply_stealth_sync(context)
            except ImportError:
                logger.debug("playwright-stealth not installed, proceeding without stealth")

            page = context.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=30_000)
            # Wait for product structured data to render (SPAs inject JSON-LD after JS runs)
            try:
                page.wait_for_selector(
                    'script[type="application/ld+json"]',
                    timeout=15_000,
                )
            except Exception:
                # Fallback: just wait a few seconds for JS to finish
                page.wait_for_timeout(5000)

            # Get the fully rendered HTML
            html = page.content()
            return self._extract_from_html(html, url)

        except Exception as e:
            logger.error("Playwright extraction failed for %s: %s", url, e)
            return None
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

    def _extract_from_html(self, html: str, url: str) -> Optional[Product]:
        """Extract product data from HTML string using extruct."""
        import extruct

        try:
            data = extruct.extract(
                html,
                base_url=url,
                syntaxes=["json-ld", "opengraph", "microdata"],
                uniform=True,
            )
        except Exception as e:
            logger.error("extruct extraction failed: %s", e)
            return None

        # Try JSON-LD first (highest quality)
        product = self._from_json_ld(data.get("json-ld", []), url)
        if product:
            return product

        # Try OpenGraph
        product = self._from_opengraph(data.get("opengraph", []), url, html)
        if product:
            return product

        # Try microdata
        product = self._from_microdata(data.get("microdata", []), url)
        if product:
            return product

        return None

    # -------------------------------------------------------------------
    # JSON-LD parsing
    # -------------------------------------------------------------------

    def _from_json_ld(
        self, items: List[Dict], url: str
    ) -> Optional[Product]:
        """Parse schema.org/Product from JSON-LD."""
        for item in items:
            item_type = item.get("@type", "")
            # Handle both string and list types
            if isinstance(item_type, list):
                types = [t.lower() for t in item_type]
            else:
                types = [item_type.lower()]

            if "product" not in types:
                continue

            name = item.get("name", "")
            brand = self._extract_brand_jsonld(item, url)
            price = self._extract_price_jsonld(item)
            image = self._extract_image(item.get("image"))
            description = item.get("description", "")

            # Split name into brand + model
            model = self._extract_model(name, brand)

            # Category (detect early so we can pass it to size/color)
            category = _detect_category(name + " " + description)

            # Gender from URL patterns and product text
            gender = _detect_gender(name + " " + description, url)

            # Size from additionalProperty or variant (category-aware)
            size = self._extract_size_jsonld(item, name, description, category)

            # Color from additionalProperty or name
            color = self._extract_color_jsonld(item, name, description)

            # Product identifiers (SKU, UPC/GTIN, MPN)
            sku, upc, mpn = self._extract_identifiers_jsonld(item)

            return Product(
                brand=brand or "Unknown",
                model=model or name,
                size=size,
                color=color,
                retail_price=price,
                url=url,
                category=category,
                gender=gender,
                image_url=image,
                description=description[:500] if description else None,
                sku=sku,
                upc=upc,
                mpn=mpn,
            )

        return None

    def _extract_brand_jsonld(self, item: Dict, url: str = "") -> str:
        """Extract brand from JSON-LD Product, falling back to URL domain."""
        brand = item.get("brand")
        if isinstance(brand, dict):
            name = brand.get("name", "")
            if name:
                return name
        if isinstance(brand, str) and brand:
            return brand

        # Fallback: extract brand from URL domain
        if url:
            return self._brand_from_domain(url)
        return "Unknown"

    @staticmethod
    def _brand_from_domain(url: str) -> str:
        """Extract a brand name from the URL domain as a last resort."""
        from urllib.parse import urlparse
        try:
            host = urlparse(url).hostname or ""
        except Exception:
            return "Unknown"
        # Strip www. and TLD
        host = host.lower().removeprefix("www.")
        domain = host.split(".")[0] if "." in host else host
        # Map known retailer domains to brand names
        DOMAIN_BRANDS = {
            "abercrombie": "Abercrombie & Fitch",
            "nike": "Nike",
            "adidas": "Adidas",
            "zara": "Zara",
            "hm": "H&M",
            "uniqlo": "Uniqlo",
            "gap": "Gap",
            "nordstrom": "Nordstrom",
            "jcrew": "J.Crew",
            "urbanoutfitters": "Urban Outfitters",
            "asos": "ASOS",
            "levi": "Levi's",
            "patagonia": "Patagonia",
            "carhartt": "Carhartt",
        }
        if domain in DOMAIN_BRANDS:
            return DOMAIN_BRANDS[domain]
        # Capitalize domain as a guess
        return domain.capitalize()

    def _extract_price_jsonld(self, item: Dict) -> float:
        """Extract price from JSON-LD Product."""
        # offers can be a dict or list
        offers = item.get("offers")
        if not offers:
            return 0.0

        if isinstance(offers, list):
            offers = offers[0] if offers else {}
        if isinstance(offers, dict):
            price = offers.get("price")
            if price is not None:
                try:
                    return float(price)
                except (ValueError, TypeError):
                    pass
            low = offers.get("lowPrice")
            if low is not None:
                try:
                    return float(low)
                except (ValueError, TypeError):
                    pass
        return 0.0

    def _extract_size_jsonld(
        self, item: Dict, name: str, description: str,
        category: Category = None,
    ) -> str:
        """Extract size from JSON-LD additionalProperty or text."""
        # Check additionalProperty
        props = item.get("additionalProperty", [])
        if isinstance(props, list):
            for prop in props:
                if isinstance(prop, dict):
                    prop_name = prop.get("name", "").lower()
                    if prop_name in ("size", "shoe size", "clothing size"):
                        return str(prop.get("value", "Unknown"))

        # Check variants/model
        variants = item.get("hasVariant", item.get("model", []))
        if isinstance(variants, list):
            for v in variants:
                if isinstance(v, dict):
                    v_props = v.get("additionalProperty", [])
                    if isinstance(v_props, list):
                        for prop in v_props:
                            if isinstance(prop, dict):
                                if prop.get("name", "").lower() == "size":
                                    return str(prop.get("value", "Unknown"))

        # Fall back to text extraction (category-aware)
        return _extract_size_from_text(name + " " + description, category)

    def _extract_color_jsonld(
        self, item: Dict, name: str, description: str
    ) -> str:
        """Extract color from JSON-LD additionalProperty or text."""
        # Check additionalProperty
        props = item.get("additionalProperty", [])
        if isinstance(props, list):
            for prop in props:
                if isinstance(prop, dict):
                    prop_name = prop.get("name", "").lower()
                    if prop_name in ("color", "colour"):
                        return str(prop.get("value", "Unknown"))

        # Check color field directly
        color = item.get("color")
        if color:
            if isinstance(color, str):
                return color
            if isinstance(color, dict):
                return color.get("name", str(color))

        # Fall back to text extraction
        return _extract_color_from_text(name + " " + description)

    def _extract_identifiers_jsonld(
        self, item: Dict
    ) -> tuple:
        """Extract SKU, UPC/GTIN, and MPN from JSON-LD Product.

        Checks direct fields first, then additionalProperty array,
        then offers for nested identifiers.

        Returns:
            Tuple of (sku, upc, mpn) — each Optional[str].
        """
        sku = None
        upc = None
        mpn = None

        # Direct fields on the Product item
        if item.get("sku"):
            sku = str(item["sku"]).strip()
        if item.get("gtin13"):
            upc = str(item["gtin13"]).strip()
        elif item.get("gtin12"):
            upc = str(item["gtin12"]).strip()
        elif item.get("gtin"):
            upc = str(item["gtin"]).strip()
        if item.get("mpn"):
            mpn = str(item["mpn"]).strip()

        # Check additionalProperty for identifiers
        props = item.get("additionalProperty", [])
        if isinstance(props, list):
            for prop in props:
                if not isinstance(prop, dict):
                    continue
                prop_name = prop.get("name", "").lower().strip()
                prop_value = str(prop.get("value", "")).strip()
                if not prop_value:
                    continue
                if prop_name in ("sku", "style", "style number", "item number"):
                    if not sku:
                        sku = prop_value
                elif prop_name in ("upc", "ean", "gtin", "gtin13", "gtin12", "barcode"):
                    if not upc:
                        upc = prop_value
                elif prop_name in ("mpn", "manufacturer part number", "part number"):
                    if not mpn:
                        mpn = prop_value

        # Check inside offers for identifiers (some retailers nest them there)
        offers = item.get("offers")
        if offers:
            offer_list = offers if isinstance(offers, list) else [offers]
            for offer in offer_list:
                if not isinstance(offer, dict):
                    continue
                if not sku and offer.get("sku"):
                    sku = str(offer["sku"]).strip()
                if not upc and offer.get("gtin13"):
                    upc = str(offer["gtin13"]).strip()
                elif not upc and offer.get("gtin12"):
                    upc = str(offer["gtin12"]).strip()
                if not mpn and offer.get("mpn"):
                    mpn = str(offer["mpn"]).strip()

        logger.debug("Extracted identifiers: sku=%s, upc=%s, mpn=%s", sku, upc, mpn)
        return sku, upc, mpn

    def _extract_image(self, image_data: Any) -> Optional[str]:
        """Extract image URL from JSON-LD image field."""
        if not image_data:
            return None
        if isinstance(image_data, str):
            return image_data
        if isinstance(image_data, list):
            first = image_data[0] if image_data else None
            if isinstance(first, str):
                return first
            if isinstance(first, dict):
                return first.get("url") or first.get("contentUrl")
        if isinstance(image_data, dict):
            return image_data.get("url") or image_data.get("contentUrl")
        return None

    def _extract_model(self, name: str, brand: str) -> str:
        """Extract model name from product name by removing brand prefix."""
        if not name:
            return ""
        if brand and brand.lower() != "unknown":
            # Remove brand from start of name
            name_lower = name.lower()
            brand_lower = brand.lower()
            if name_lower.startswith(brand_lower):
                model = name[len(brand):].strip(" -/")
                return model if model else name
            # Also try common brand positions
            for prefix in [brand_lower + " ", brand_lower + " - "]:
                if name_lower.startswith(prefix):
                    return name[len(prefix):].strip()
        return name

    # -------------------------------------------------------------------
    # OpenGraph parsing
    # -------------------------------------------------------------------

    def _from_opengraph(
        self, items: List[Dict], url: str, html: str = ""
    ) -> Optional[Product]:
        """Parse product data from OpenGraph tags."""
        for item in items:
            og_type = item.get("og:type", "")
            title = item.get("og:title", "")
            description = item.get("og:description", "")
            image = item.get("og:image")
            price = 0.0

            # Price from OG or product-specific tags
            price_str = (
                item.get("product:price:amount")
                or item.get("og:price:amount")
                or ""
            )
            if price_str:
                try:
                    price = float(price_str)
                except (ValueError, TypeError):
                    pass

            if not title:
                continue

            from ..matchers.brand_aliases import resolve_brand
            brand = resolve_brand(title) or "Unknown"
            model = self._extract_model(title, brand)
            category = _detect_category(title + " " + description)
            gender = _detect_gender(title + " " + description, url)
            size = _extract_size_from_text(title + " " + description, category)
            color = _extract_color_from_text(title + " " + description)

            return Product(
                brand=brand,
                model=model or title,
                size=size,
                color=color,
                retail_price=price,
                url=url,
                category=category,
                gender=gender,
                image_url=image,
                description=description[:500] if description else None,
            )

        return None

    # -------------------------------------------------------------------
    # Microdata parsing
    # -------------------------------------------------------------------

    def _from_microdata(
        self, items: List[Dict], url: str
    ) -> Optional[Product]:
        """Parse schema.org/Product from microdata."""
        for item in items:
            item_type = item.get("@type", "")
            if isinstance(item_type, list):
                types = [t.lower() for t in item_type]
            else:
                types = [item_type.lower()]
            if "product" in types:
                # Reuse JSON-LD parser since extruct uniform=True
                # normalizes microdata to same shape
                return self._from_json_ld([item], url)
        return None


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------

def _detect_category(text: str) -> Category:
    """Detect product category from text using keyword matching."""
    if not text:
        return Category.UNKNOWN
    text_lower = text.lower()
    # Check each category's keywords
    best_cat = Category.UNKNOWN
    best_count = 0
    for cat, keywords in _CATEGORY_KEYWORDS.items():
        count = sum(1 for kw in keywords if kw in text_lower)
        if count > best_count:
            best_count = count
            best_cat = cat
    return best_cat


def _detect_gender(text: str, url: str) -> Gender:
    """Detect target gender from product text and URL.

    URL patterns are checked first (more reliable than text heuristics)
    since retailer URLs consistently encode gender in the path or query.

    Text matching uses regex word boundaries to avoid false positives
    (e.g., "men" matching inside "women").
    """
    url_lower = url.lower()

    # URL patterns (most reliable signal)
    # Check womens first since "/women/" would also match a naive "/men/" check
    womens_url_patterns = ["/women/", "/womens/", "/women-", "gender=women", "gender=female"]
    mens_url_patterns = ["/men/", "/mens/", "/men-", "gender=men", "gender=male"]

    if any(p in url_lower for p in womens_url_patterns):
        return Gender.WOMENS
    if any(p in url_lower for p in mens_url_patterns):
        return Gender.MENS
    if "/unisex/" in url_lower or "gender=unisex" in url_lower:
        return Gender.UNISEX

    # Text matching with word boundaries to avoid "men" matching "women"
    text_lower = text.lower()

    # Check womens patterns first (more specific — "women" contains "men")
    womens_patterns = [
        r"\bwomen'?s?\b", r"\bfemale\b", r"\bher\b",
        r"\bladies\b", r"\bgirls?\b",
    ]
    mens_patterns = [
        r"\bmen'?s?\b", r"\bmale\b", r"\bhim\b",
        r"\bguys?\b", r"\bboys?\b",
    ]

    # Score using regex (womens patterns won't false-positive on "men")
    womens_score = sum(
        1 for p in womens_patterns if re.search(p, text_lower)
    )
    # For mens, exclude matches that are actually inside "women"
    mens_score = 0
    for p in mens_patterns:
        m = re.search(p, text_lower)
        if m:
            start = m.start()
            # Skip if this "men" match is preceded by "wo" (part of "women")
            if p == r"\bmen'?s?\b" and start >= 2 and text_lower[start-2:start] == "wo":
                continue
            mens_score += 1

    if womens_score > mens_score:
        return Gender.WOMENS
    if mens_score > womens_score:
        return Gender.MENS

    return Gender.UNKNOWN


def _detect_gender_from_title(title: str) -> Gender:
    """Quick gender detection from a listing title string.

    Used by the coordinator to filter search results after retrieval.
    Lighter-weight than _detect_gender (no URL analysis).
    Checks womens first to avoid "men" matching inside "women".
    """
    title_lower = title.lower()

    # Check womens first (more specific — avoids "men" in "women" false positive)
    if re.search(r"\bwomen'?s?\b", title_lower):
        return Gender.WOMENS
    if re.search(r"\bladies\b", title_lower):
        return Gender.WOMENS
    if re.search(r"\bfemale\b", title_lower):
        return Gender.WOMENS

    # Now check mens (safe since we already handled "women" above)
    if re.search(r"\bmen'?s?\b", title_lower):
        return Gender.MENS
    if re.search(r"\bmale\b", title_lower):
        return Gender.MENS

    return Gender.UNKNOWN


def _extract_size_from_text(text: str, category: Category = None) -> str:
    """Extract size from free-form text.

    Args:
        text: Free-form text containing size information.
        category: Product category for context-aware extraction.
                  When SHOES, prioritizes shoe-size patterns over letter sizes.
                  When BOTTOMS, prioritizes waist patterns.
    """
    if not text:
        return "Unknown"

    # --- Category-prioritized extraction ---

    if category == Category.SHOES:
        # For shoes: try shoe patterns FIRST, skip letter sizes entirely
        m = _SIZE_SHOE_RE.search(text)
        if m:
            val = float(m.group(1))
            return str(int(val)) if val == int(val) else str(val)
        # Fallback: standalone number in shoe-size range (6-15, half sizes)
        for m in _SIZE_SHOE_STANDALONE_RE.finditer(text):
            val = float(m.group(1))
            if 6.0 <= val <= 15.0:
                return str(int(val)) if val == int(val) else str(val)
        # Numeric size as last resort
        m = _SIZE_NUMERIC_RE.search(text)
        if m:
            return m.group(1)
        return "Unknown"

    if category == Category.BOTTOMS:
        # For bottoms: try waist patterns first
        m = _SIZE_WAIST_RE.search(text)
        if m:
            return f"{m.group(1)}x{m.group(2)}"
        # Then letter sizes (S, M, L are valid for bottoms too)
        m = _SIZE_LETTER_RE.search(text)
        if m:
            return m.group(1).upper()
        # Then numeric size
        m = _SIZE_NUMERIC_RE.search(text)
        if m:
            return m.group(1)
        return "Unknown"

    # --- Default order (no category or non-shoe/bottom categories) ---

    # Waist x inseam
    m = _SIZE_WAIST_RE.search(text)
    if m:
        return f"{m.group(1)}x{m.group(2)}"

    # Shoe size (with prefix)
    m = _SIZE_SHOE_RE.search(text)
    if m:
        val = float(m.group(1))
        return str(int(val)) if val == int(val) else str(val)

    # Letter size
    m = _SIZE_LETTER_RE.search(text)
    if m:
        return m.group(1).upper()

    # Numeric size
    m = _SIZE_NUMERIC_RE.search(text)
    if m:
        return m.group(1)

    return "Unknown"


def _extract_color_from_text(text: str) -> str:
    """Extract the most likely color from free-form text.

    Handles slash-separated colorways like "White/Black" or
    "Sail/University Red/Gum Medium Brown" by splitting on "/" and
    checking each segment independently.
    """
    if not text:
        return "Unknown"

    # Split on "/" to handle colorways like "White/Black"
    # Check each segment AND the full text (for multi-word colors spanning segments)
    segments = [text]
    if "/" in text:
        segments = [s.strip() for s in text.split("/") if s.strip()] + segments

    for segment in segments:
        seg_lower = segment.lower()

        # Multi-word colors first (more specific)
        multi_word_colors = [
            "off white", "off-white", "heather grey", "heather gray",
            "forest green", "royal blue", "sky blue", "light blue",
            "dark blue", "dark green", "light grey", "light gray",
            "burnt orange",
        ]
        for color in multi_word_colors:
            if color in seg_lower:
                return color.title()

        # Single word colors
        for color in _COLOR_WORDS:
            # Word boundary check to avoid matching "tan" in "stain"
            pattern = r"\b" + re.escape(color) + r"\b"
            if re.search(pattern, seg_lower):
                return color.title()

    return "Unknown"
