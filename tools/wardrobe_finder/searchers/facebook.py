"""
Facebook Marketplace searcher using Playwright MCP with Brave browser.

Uses Playwright MCP tools to control your logged-in Brave browser session
to search Facebook Marketplace, avoiding bot detection.

This searcher operates differently from others:
- Must be invoked by {{ORCHESTRATOR_NAME}} (requires MCP tools in Claude Code session)
- Uses your real Brave browser where you're logged into Facebook
- Cannot run as a standalone CLI script
- Designed for {{ORCHESTRATOR_NAME}}-orchestrated searches only

WORKFLOW:
1. User runs: wardrobe_finder.py search <url>
2. CLI detects Facebook is enabled
3. CLI writes search request to ~/.wardrobe/facebook_request.json
4. CLI tells {{ORCHESTRATOR_NAME}}: "Facebook search needed, please run it"
5. {{ORCHESTRATOR_NAME}} reads request file, uses MCP tools to search
6. {{ORCHESTRATOR_NAME}} writes results to ~/.wardrobe/facebook_results.json
7. CLI reads results and displays them
"""

import json
import re
import sys
from pathlib import Path
from typing import List, Optional
from urllib.parse import quote_plus

try:
    from .base import SearcherBase
    from ..models import Product, SearchResult, Condition, parse_condition
except ImportError:
    # Allow standalone syntax checking
    SearcherBase = object  # type: ignore
    Product = None  # type: ignore
    SearchResult = None  # type: ignore
    Condition = None  # type: ignore
    parse_condition = None  # type: ignore


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_BASE_URL = "https://www.facebook.com"
_SEARCH_PATH = "/marketplace/category/clothing"
_PAGE_LOAD_TIMEOUT = 15_000  # ms


def _log(msg: str) -> None:
    """Log to stderr for debugging."""
    print(f"[facebook] {msg}", file=sys.stderr)


def _parse_price(text: str) -> Optional[float]:
    """Extract a numeric price from text like '$55' or '$1,200'."""
    if not text:
        return None
    match = re.search(r"\$[\s]*([\d,]+(?:\.\d{1,2})?)", text)
    if match:
        return float(match.group(1).replace(",", ""))
    return None


class FacebookMarketplaceSearcher(SearcherBase if isinstance(SearcherBase, type) else object):
    """
    Facebook Marketplace searcher via Claude in Chrome MCP.

    IMPORTANT: This searcher cannot run standalone. It must be called
    from within a Claude Code session with MCP tools available.
    """

    name: str = "facebook"

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def search(self, product, max_results: int = 20) -> list:
        """
        Search Facebook Marketplace for product.

        This method will raise NotImplementedError when called directly.
        Facebook searches must be orchestrated by {{ORCHESTRATOR_NAME}} using MCP tools.
        """
        raise NotImplementedError(
            "Facebook Marketplace searches must be run through {{ORCHESTRATOR_NAME}} "
            "using Claude in Chrome MCP tools. This searcher cannot run "
            "as a standalone CLI command."
        )

    def available(self) -> bool:
        """
        Return False - this searcher requires MCP tools from Claude Code.
        """
        return False


# ---------------------------------------------------------------------------
# Request/Response file paths for CLI <-> {{ORCHESTRATOR_NAME}} handoff
# ---------------------------------------------------------------------------

WARDROBE_DIR = Path.home() / ".wardrobe"
FACEBOOK_REQUEST_FILE = WARDROBE_DIR / "facebook_request.json"
FACEBOOK_RESULTS_FILE = WARDROBE_DIR / "facebook_results.json"

# ---------------------------------------------------------------------------
# MCP-based search implementation (for {{ORCHESTRATOR_NAME}})
# ---------------------------------------------------------------------------

def build_search_url(product) -> str:
    """
    Build Facebook Marketplace search URL from product details.

    Args:
        product: Product object with brand, model, category, size

    Returns:
        Full search URL for Facebook Marketplace

    Example:
        >>> from wardrobe_finder.models import Product, Category
        >>> p = Product(brand="Nike", model="Air Force 1", category=Category.SHOES, size="10.5")
        >>> build_search_url(p)
        'https://www.facebook.com/marketplace/category/clothing?query=Nike+Air+Force+1&exact=false'
    """
    query_parts = []

    if product.brand:
        query_parts.append(product.brand)
    if product.model:
        query_parts.append(product.model)

    # Add size if available
    if product.size:
        query_parts.append(f"size {product.size}")

    query = " ".join(query_parts)
    encoded_query = quote_plus(query)

    return f"{_BASE_URL}{_SEARCH_PATH}?query={encoded_query}&exact=false"


def extract_listing_from_element(element_html: str) -> Optional[dict]:
    """
    Extract listing data from a Facebook Marketplace listing element.

    Args:
        element_html: HTML string of a single marketplace listing card

    Returns:
        Dict with keys: title, price, url, image_url, location
        Returns None if parsing fails

    Facebook Marketplace listing structure (as of 2026-02):
    - Listings are in cards with data-testid or aria-label attributes
    - Price is in span elements, format: "$XX" or "$X,XXX"
    - Title is in anchor text
    - URL is in href attribute (relative path starting with /marketplace/item/)
    - Image is in img tag with src
    - Location may be in separate span below price
    """
    try:
        # This is a placeholder - actual implementation would parse HTML
        # In practice, {{ORCHESTRATOR_NAME}} would use MCP tools to click and extract data
        # from the live browser DOM
        _log("Parsing Facebook listing element (MCP-based extraction)")
        return None
    except Exception as e:
        _log(f"Failed to parse listing element: {e}")
        return None


# ---------------------------------------------------------------------------
# {{ORCHESTRATOR_NAME}} orchestration guide (embedded documentation)
# ---------------------------------------------------------------------------

FACEBOOK_SEARCH_WORKFLOW = """
Facebook Marketplace Search Workflow for {{ORCHESTRATOR_NAME}}

PREREQUISITE:
- {{USER_NAME}} must be logged into Facebook in Brave browser
- Playwright MCP tools must be available

HOW TO INVOKE:
When CLI requests Facebook search, {{ORCHESTRATOR_NAME}} should:

1. Read search request:
   request = json.loads(Path("~/.wardrobe/facebook_request.json").read_text())
   product = request["product"]  # Has brand, model, size, category

2. Build search URL:
   from wardrobe_finder.searchers.facebook import build_search_url
   url = build_search_url(product)

3. Navigate to Facebook Marketplace:
   mcp__playwright__browser_navigate(url=url)

4. Wait for listings to load (3-5 seconds for dynamic content)

5. Extract listings with JavaScript:
   mcp__playwright__browser_evaluate with:
   ```javascript
   Array.from(document.querySelectorAll('a[href*="/marketplace/item/"]'))
     .slice(0, 20)
     .map(link => {
       const getText = (sel) => link.querySelector(sel)?.textContent?.trim() || '';
       const priceText = getText('span'); // First span usually has price
       return {
         title: link.getAttribute('aria-label') || getText('span'),
         price: priceText,
         url: link.href,
         image: link.querySelector('img')?.src || '',
         location: getText('[data-testid*="location"]') || ''
       };
     })
     .filter(item => item.price && item.price.includes('$'));
   ```

6. Convert results:
   from wardrobe_finder.searchers.facebook import format_results_for_cli
   results = format_results_for_cli(raw_listings, product)

7. Write results file:
   Path("~/.wardrobe/facebook_results.json").write_text(json.dumps({
     "results": [r.to_dict() for r in results],
     "timestamp": datetime.now().isoformat()
   }))

8. Tell CLI: "Facebook search complete, {len(results)} results written"

ERROR HANDLING:
- If not logged in: Write empty results with error message
- If no results: Write empty list
- If scraping fails: Write empty list with error in response

IMPORTANT:
- This workflow is for {{ORCHESTRATOR_NAME}} ONLY
- Cannot be automated in CLI
- Requires human approval for each search (don't spam Facebook)
"""


def format_results_for_cli(listings: List[dict], product) -> List:
    """
    Convert raw Facebook listing dicts to SearchResult objects.

    Args:
        listings: List of dicts from MCP extraction
        product: Original Product search query

    Returns:
        List of SearchResult objects
    """
    results = []

    for listing in listings:
        try:
            # Parse price
            price = _parse_price(listing.get("price", ""))
            if price is None:
                continue

            # Determine condition (default to "good")
            title = listing.get("title", "")
            if "new" in title.lower() or "nwt" in title.lower():
                condition = Condition.NWT
            elif "like new" in title.lower():
                condition = Condition.LIKE_NEW
            else:
                condition = Condition.GOOD  # Default for secondhand

            # Build full URL if relative
            url = listing.get("url", "")
            if url.startswith("/marketplace"):
                url = f"{_BASE_URL}{url}"

            # Create result
            result = SearchResult(
                platform="facebook",
                title=title,
                price=price,
                size=product.size or "Unknown",  # Assume matches search
                color=product.color or "Unknown",
                condition=condition,
                url=url,
                thumbnail=listing.get("image", ""),
            )
            results.append(result)

        except Exception as e:
            _log(f"Failed to convert listing: {e}")
            continue

    return sorted(results, key=lambda r: r.price)


# ---------------------------------------------------------------------------
# Module exports
# ---------------------------------------------------------------------------

__all__ = [
    "FacebookMarketplaceSearcher",
    "build_search_url",
    "extract_listing_from_element",
    "format_results_for_cli",
    "FACEBOOK_SEARCH_WORKFLOW",
]
