"""
eBay Browse API searcher.

Uses the official eBay Browse API (search endpoint) with OAuth 2.0
Client Credentials grant (application token — no user login needed).

Credentials from environment:
    EBAY_APP_ID    — eBay application ID (client_id)
    EBAY_CERT_ID   — eBay cert ID (client_secret)

Token caching: application tokens expire after ~2 hours. We cache them
in memory and refresh automatically when expired.
"""

import base64
import json
import logging
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional

from .base import SearcherBase
from ..models import (
    Category, Condition, Product, SearchResult, parse_condition,
)
from ..matchers.size_converter import extract_size_from_text

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# eBay API constants
# ---------------------------------------------------------------------------

EBAY_AUTH_URL = "https://api.ebay.com/identity/v1/oauth2/token"
EBAY_BROWSE_URL = "https://api.ebay.com/buy/browse/v1/item_summary/search"

# Use the broad parent category for all searches.
# Previously this mapped to gender-specific subcategories (e.g., men's shoes
# only), which caused women's searches to miss results.  Letting eBay's search
# relevance + aspect filters (brand, size) handle narrowing is more reliable.
EBAY_PARENT_CATEGORY = "11450"  # Clothing, Shoes & Accessories

# eBay condition IDs
EBAY_CONDITION_MAP = {
    "1000": Condition.NWT,       # New with tags
    "1500": Condition.NWOT,      # New without tags
    "1750": Condition.LIKE_NEW,  # New with defects
    "2500": Condition.LIKE_NEW,  # Seller refurbished
    "3000": Condition.GOOD,      # Used
    "7000": Condition.FAIR,      # For parts or not working
}


class EbayApiSearcher(SearcherBase):
    """Search eBay via the official Browse API."""

    name = "ebay"

    def __init__(self):
        self._app_id = os.environ.get("EBAY_APP_ID", "")
        self._cert_id = os.environ.get("EBAY_CERT_ID", "")
        self._token: Optional[str] = None
        self._token_expiry: float = 0.0

    def is_available(self) -> bool:
        """Available if both EBAY_APP_ID and EBAY_CERT_ID are set."""
        return bool(self._app_id and self._cert_id)

    def search(
        self, product: Product, max_results: int = 20
    ) -> List[SearchResult]:
        """Search eBay for matching products."""
        if not self.is_available():
            logger.warning("eBay credentials not configured, skipping")
            return []

        # Ensure valid token
        token = self._get_token()
        if not token:
            logger.error("Failed to obtain eBay auth token")
            return []

        # Build search query
        query = product.search_query()
        if not query:
            logger.warning("Empty search query, skipping eBay search")
            return []

        # Build request parameters
        params = {
            "q": query,
            "limit": str(min(max_results, 50)),  # eBay max is 200
            "sort": "price",
        }

        # Use broad parent category — let aspect filters narrow results
        params["category_ids"] = EBAY_PARENT_CATEGORY

        # Add aspect filters for brand
        aspect_filters = []
        if product.brand and product.brand.lower() != "unknown":
            aspect_filters.append(f"Brand:{{{product.brand}}}")
        if aspect_filters:
            params["aspect_filter"] = ",".join(aspect_filters)

        # Add GTIN filter if product has a UPC/EAN
        if product.upc:
            params["gtin"] = product.upc

        # Add filter for used/pre-owned items (the whole point)
        params["filter"] = "conditions:{1000|1500|1750|2500|3000}"

        url = f"{EBAY_BROWSE_URL}?{urllib.parse.urlencode(params)}"
        logger.debug("eBay search URL: %s", url)

        try:
            req = urllib.request.Request(
                url,
                headers={
                    "Authorization": f"Bearer {token}",
                    "X-EBAY-C-MARKETPLACE-ID": "EBAY_US",
                    "Content-Type": "application/json",
                },
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, json.JSONDecodeError) as e:
            logger.error("eBay API request failed: %s", e)
            return []

        return self._parse_results(data, product.category)

    # -------------------------------------------------------------------
    # Token management
    # -------------------------------------------------------------------

    def _get_token(self) -> Optional[str]:
        """Get a valid application token, refreshing if expired."""
        now = time.time()
        if self._token and now < self._token_expiry:
            return self._token

        return self._refresh_token()

    def _refresh_token(self) -> Optional[str]:
        """Request a new application token using Client Credentials grant."""
        credentials = f"{self._app_id}:{self._cert_id}"
        encoded = base64.b64encode(credentials.encode()).decode()

        body = urllib.parse.urlencode({
            "grant_type": "client_credentials",
            "scope": "https://api.ebay.com/oauth/api_scope",
        }).encode()

        try:
            req = urllib.request.Request(
                EBAY_AUTH_URL,
                data=body,
                headers={
                    "Authorization": f"Basic {encoded}",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            self._token = data.get("access_token")
            expires_in = data.get("expires_in", 7200)
            # Refresh 5 minutes before expiry
            self._token_expiry = time.time() + expires_in - 300
            logger.debug(
                "eBay token refreshed, expires in %d seconds", expires_in
            )
            return self._token
        except (urllib.error.URLError, json.JSONDecodeError, KeyError) as e:
            logger.error("eBay token refresh failed: %s", e)
            return None

    # -------------------------------------------------------------------
    # Response parsing
    # -------------------------------------------------------------------

    def _parse_results(
        self, data: Dict[str, Any], category: Category
    ) -> List[SearchResult]:
        """Parse eBay Browse API response into SearchResult objects."""
        results = []
        items = data.get("itemSummaries", [])

        for item in items:
            title = item.get("title", "")
            price_data = item.get("price", {})
            price = 0.0
            try:
                price = float(price_data.get("value", 0))
            except (ValueError, TypeError):
                pass

            # Condition
            condition_id = item.get("conditionId", "")
            condition = EBAY_CONDITION_MAP.get(
                str(condition_id), Condition.UNKNOWN
            )
            # Also check title for condition hints
            if condition == Condition.UNKNOWN:
                condition = parse_condition(title)

            # Extract size from title (eBay doesn't always have structured size)
            size = extract_size_from_text(title, category)

            # Color from title
            color = self._extract_color(item, title)

            # URL
            url = item.get("itemWebUrl", item.get("itemHref", ""))

            # Thumbnail
            image = item.get("image", {})
            thumbnail = image.get("imageUrl") if isinstance(image, dict) else None

            results.append(SearchResult(
                platform="eBay",
                title=title,
                price=price,
                size=size,
                color=color,
                condition=condition,
                url=url,
                thumbnail=thumbnail,
            ))

        return results

    def _extract_color(self, item: Dict, title: str) -> str:
        """Extract color from eBay item data or title."""
        # Check itemAffiliateWebUrl -> aspects
        # eBay sometimes includes color in localizedAspects
        aspects = item.get("localizedAspects", [])
        if isinstance(aspects, list):
            for aspect in aspects:
                if isinstance(aspect, dict):
                    if aspect.get("name", "").lower() == "color":
                        return aspect.get("value", "Unknown")

        # Fall back to title
        from ..extractors.structured_data import _extract_color_from_text
        return _extract_color_from_text(title)
