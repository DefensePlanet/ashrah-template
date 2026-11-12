"""
Search coordinator — orchestrates parallel searches across marketplaces.

Discovers available searchers, runs them concurrently via ThreadPoolExecutor,
scores results, and returns them sorted by match quality then price.

Supports three matching enhancement layers:
1. SKU/UPC secondary searches (if product has identifiers)
2. AI query expansion via Gemini Flash (if --no-expand not set)
3. Vision matching via Gemini Flash Vision (if --no-vision not set)
"""

import importlib
import logging
import os
import pkgutil
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Set, Tuple

from .models import Condition, Gender, Product, SearchResult, UserProfile
from .matchers.scorer import score_match
from .matchers.semantic import expand_queries
from .matchers.vision import score_visual_matches
from .searchers.base import SearcherBase

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Size matching helpers
# ---------------------------------------------------------------------------

# Ordered letter sizes for adjacency matching
_LETTER_SIZES = ["XXS", "XS", "S", "M", "L", "XL", "XXL", "XXXL", "3XL", "4XL"]

# Common aliases that should map to canonical forms
_SIZE_ALIASES: Dict[str, str] = {
    "EXTRA SMALL": "XS",
    "SMALL": "S",
    "MEDIUM": "M",
    "LARGE": "L",
    "EXTRA LARGE": "XL",
    "2XL": "XXL",
    "3XL": "XXXL",
    "SM": "S",
    "MED": "M",
    "LG": "L",
    "XLG": "XL",
    "XLARGE": "XL",
}


def _normalize_size(size: str) -> str:
    """Normalize a size string for comparison.

    Strips whitespace, removes common prefixes like 'Size' or 'Sz',
    uppercases, and resolves common aliases (e.g. 'Medium' -> 'M').
    """
    if not size:
        return ""
    size = size.upper().strip()
    # Remove common prefixes
    for prefix in ("SIZE ", "SZ ", "US ", "UK "):
        if size.startswith(prefix):
            size = size[len(prefix):]
    size = size.strip()
    # Resolve aliases
    return _SIZE_ALIASES.get(size, size)


def _size_matches(target: str, result: str) -> bool:
    """Check if a result's size matches the target size.

    Rules:
    - Unknown/empty result sizes pass through (we can't exclude them).
    - Exact match always passes.
    - Slash-separated sizes (e.g. 'M/L') pass if either half matches.
    - Letter sizes allow +/- 1 adjacency (M matches S and L).
    - Numeric sizes require exact match (shoe sizes, waist sizes).
    """
    if not result or result == "UNKNOWN":
        return True  # Unknown sizes pass through — can't exclude

    # Exact match
    if target == result:
        return True

    # Slash-separated sizes (e.g. 'M/L', 'S/M')
    if "/" in result:
        parts = [p.strip() for p in result.split("/")]
        return any(_size_matches(target, p) for p in parts)

    # Letter sizes: allow +/- 1 adjacency
    if target in _LETTER_SIZES and result in _LETTER_SIZES:
        target_idx = _LETTER_SIZES.index(target)
        result_idx = _LETTER_SIZES.index(result)
        return abs(target_idx - result_idx) <= 1

    # Numeric sizes: exact match only (shoe sizes, waist sizes)
    return False


# ---------------------------------------------------------------------------
# Comprehensive result quality scoring
# ---------------------------------------------------------------------------


def _score_results(
    product: Product,
    results: List[SearchResult],
    vision_scores: Dict[str, float],
) -> List[SearchResult]:
    """Score search results for match quality.

    Combines multiple quality signals into a single 0-100 score:
    - Title match (50%): Brand, model, and color keyword matching
    - Size match (15%): Exact vs adjacent vs unknown
    - Vision match (20%): Visual similarity from CLIP or Codex
    - Price (10%): Lower is better (normalized across result set)
    - Condition (5%): NWT > Like New > Good > Fair

    When vision scores are unavailable (empty dict), the 20% vision
    weight is redistributed proportionally across title (62.5%),
    size (18.75%), price (12.5%), and condition (6.25%).

    Args:
        product: The target product.
        results: Filtered search results.
        vision_scores: Dict mapping result URL to vision score (0.0-1.0).
            Empty dict if vision matching was skipped or unavailable.

    Returns:
        The same results list with match_score updated (0-100 int).
    """
    if not results:
        return results

    # Determine weights based on whether vision scores are available
    has_vision = bool(vision_scores)
    if has_vision:
        w_title = 50.0
        w_size = 15.0
        w_vision = 20.0
        w_price = 10.0
        w_condition = 5.0
    else:
        # Redistribute vision weight proportionally across other signals
        w_title = 62.5
        w_size = 18.75
        w_vision = 0.0
        w_price = 12.5
        w_condition = 6.25

    # Normalize price for scoring (0-1 scale, lower is better)
    prices = [r.price for r in results if r.price > 0]
    min_price = min(prices) if prices else 0
    max_price = max(prices) if prices else 1
    price_range = max_price - min_price if max_price > min_price else 1

    # Condition score lookup
    condition_scores = {
        Condition.NWT: 1.0,
        Condition.NWOT: 0.9,
        Condition.LIKE_NEW: 0.8,
        Condition.GOOD: 0.6,
        Condition.FAIR: 0.4,
        Condition.UNKNOWN: 0.5,
    }

    for result in results:
        score = 0.0

        # 1. Title match (brand + model + color keywords)
        score += _score_title_match(product, result) * w_title

        # 2. Size match
        score += _score_size_match(product, result) * w_size

        # 3. Vision match
        if has_vision:
            v_score = vision_scores.get(result.url, 0.0)
            score += v_score * w_vision

        # 4. Price (lower is better)
        if result.price > 0 and price_range > 0:
            price_score = 1.0 - ((result.price - min_price) / price_range)
            score += price_score * w_price

        # 5. Condition
        score += condition_scores.get(result.condition, 0.5) * w_condition

        result.match_score = max(0, min(100, int(round(score))))

    return results


def _score_title_match(product: Product, result: SearchResult) -> float:
    """Score 0.0-1.0 based on how well the listing title matches the product.

    Breakdown:
    - Exact brand match: 0.50
    - Exact model match: 0.40 (partial credit for word overlap)
    - Color match bonus: 0.10
    """
    title_lower = result.title.lower()
    brand_lower = product.brand.lower() if product.brand else ""
    model_lower = product.model.lower() if product.model else ""

    score = 0.0

    # Brand match (50% of title score)
    if brand_lower and brand_lower != "unknown":
        if brand_lower in title_lower:
            score += 0.5
        else:
            # Try individual brand words for multi-word brands
            # e.g. "Abercrombie & Fitch" -> check for "abercrombie"
            brand_words = [w for w in brand_lower.split() if len(w) > 2 and w != "the"]
            if brand_words:
                matches = sum(1 for w in brand_words if w in title_lower)
                if matches > 0:
                    score += 0.25 * (matches / len(brand_words))

    # Model match (40% of title score)
    if model_lower and model_lower != "unknown":
        if model_lower in title_lower:
            # Full model name found in title
            score += 0.4
        else:
            # Check individual words — partial credit
            model_words = [w for w in model_lower.split() if len(w) > 1]
            if model_words:
                matches = sum(1 for word in model_words if word in title_lower)
                word_ratio = matches / len(model_words)
                score += word_ratio * 0.4

    # Color match bonus (10% of title score)
    if product.color and product.color.lower() not in ("unknown", ""):
        if product.color.lower() in title_lower:
            score += 0.1

    return min(score, 1.0)


def _score_size_match(product: Product, result: SearchResult) -> float:
    """Score 0.0-1.0 based on size match quality.

    Returns:
    - 1.0 for exact match
    - 0.7 for adjacent letter size (M matches S or L)
    - 0.4 for two sizes away
    - 0.5 for unknown result size (benefit of the doubt)
    - 0.0 for definite mismatch
    """
    target = _normalize_size(product.size)
    result_size = _normalize_size(result.size)

    if not target or target == "UNKNOWN":
        return 0.5  # Product size unknown, neutral score

    if not result_size or result_size == "UNKNOWN":
        return 0.5  # Result size unknown, benefit of the doubt

    if target == result_size:
        return 1.0  # Exact match

    # Check adjacency for letter sizes
    if target in _LETTER_SIZES and result_size in _LETTER_SIZES:
        target_idx = _LETTER_SIZES.index(target)
        result_idx = _LETTER_SIZES.index(result_size)
        diff = abs(target_idx - result_idx)
        if diff == 1:
            return 0.7  # Adjacent size
        elif diff == 2:
            return 0.4  # Two sizes away

    # Check slash-separated sizes (e.g. "M/L")
    if "/" in result_size:
        parts = [p.strip() for p in result_size.split("/")]
        if target in parts:
            return 0.9  # One half matches exactly

    return 0.0  # No match


# ---------------------------------------------------------------------------
# Rate limits (requests per second per platform)
# ---------------------------------------------------------------------------

RATE_LIMITS: Dict[str, float] = {
    "ebay": 5.0,
    "poshmark": 1.0,
    "depop": 1.0,
    "mercari": 1.0,
    "thredup": 1.0,
    "grailed": 2.0,
    "facebook": 0.5,  # {{ORCHESTRATOR_NAME}}-only, manual searches via MCP
}


class RateLimiter:
    """Simple per-platform rate limiter using token bucket."""

    def __init__(self):
        # Pre-initialize locks for all known platforms to avoid race conditions.
        # setdefault is used in wait() as a safety net for unknown platforms.
        self._locks: Dict[str, threading.Lock] = {
            platform: threading.Lock() for platform in RATE_LIMITS
        }
        self._last_call: Dict[str, float] = {}

    def wait(self, platform: str) -> None:
        """Block until we can make a request to the given platform."""
        # setdefault is atomic under CPython's GIL — safe for unknown platforms
        lock = self._locks.setdefault(platform, threading.Lock())

        limit = RATE_LIMITS.get(platform, 1.0)
        interval = 1.0 / limit

        with lock:
            now = time.time()
            last = self._last_call.get(platform, 0.0)
            elapsed = now - last
            if elapsed < interval:
                time.sleep(interval - elapsed)
            self._last_call[platform] = time.time()


class SearchCoordinator:
    """Coordinates parallel searches across all available marketplace searchers."""

    def __init__(self):
        self._searchers: List[SearcherBase] = []
        self._rate_limiter = RateLimiter()
        self._discover_searchers()

    def _discover_searchers(self) -> None:
        """Auto-discover all SearcherBase subclasses in the searchers package."""
        # Import known searchers
        try:
            from .searchers.ebay_api import EbayApiSearcher
            self._searchers.append(EbayApiSearcher())
        except ImportError as e:
            logger.debug("eBay searcher not available: %s", e)

        # Try importing optional searchers (poshmark, depop, etc.)
        searcher_dir = os.path.join(
            os.path.dirname(__file__), "searchers"
        )
        for finder, name, ispkg in pkgutil.iter_modules([searcher_dir]):
            if name in ("base", "__init__", "ebay_api"):
                continue
            try:
                module = importlib.import_module(
                    f".searchers.{name}", package="wardrobe_finder"
                )
                # Find SearcherBase subclasses
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (
                        isinstance(attr, type)
                        and issubclass(attr, SearcherBase)
                        and attr is not SearcherBase
                    ):
                        instance = attr()
                        # Avoid duplicates by name
                        if instance.name not in [s.name for s in self._searchers]:
                            self._searchers.append(instance)
                            logger.debug("Discovered searcher: %s", instance.name)
            except Exception as e:
                logger.debug("Failed to load searcher %s: %s", name, e)

    @property
    def searchers(self) -> List[SearcherBase]:
        """Return all discovered searchers."""
        return list(self._searchers)

    def available_searchers(
        self, enabled_platforms: Optional[List[str]] = None
    ) -> List[SearcherBase]:
        """Return searchers that are both available and enabled."""
        available = []
        for s in self._searchers:
            if not s.is_available():
                logger.debug("Searcher %s not available, skipping", s.name)
                continue
            if enabled_platforms and s.name not in enabled_platforms:
                logger.debug("Searcher %s not enabled, skipping", s.name)
                continue
            available.append(s)
        return available

    def search(
        self,
        product: Product,
        profile: Optional[UserProfile] = None,
        max_results: int = 20,
        platforms: Optional[List[str]] = None,
        no_expand: bool = False,
        no_vision: bool = False,
        gender_filter: Optional[str] = None,
        size_strict: bool = True,
        min_score: int = 0,
    ) -> List[SearchResult]:
        """Run parallel searches across all available platforms.

        Supports three enhancement layers (all optional, degrade gracefully):
        1. SKU/UPC secondary searches: If product has identifiers, runs a
           second search per platform with just the SKU or UPC.
        2. AI query expansion: Uses Gemini Flash to generate alternative
           search terms, then searches with those too.
        3. Vision matching: Uses CLIP or Codex Vision to compare product
           image against listing thumbnails for visual similarity scoring.

        Args:
            product: The target product to search for.
            profile: User preferences (sizes, enabled platforms, etc.).
            max_results: Max results per platform.
            platforms: Override list of platforms (None = use profile).
            no_expand: If True, skip AI query expansion.
            no_vision: If True, skip vision matching.
            gender_filter: Filter results by gender ("mens", "womens",
                "unisex", or None/"any" for no filtering). When set,
                auto-detected gender from the product is used; explicit
                CLI flag overrides it.
            size_strict: If True, only keep results matching the product's
                size (with +/- 1 letter-size tolerance). Default True.
            min_score: Minimum match score (0-100) to include in results.
                Results below this threshold are filtered out. Default 0.

        Returns:
            Combined results sorted by match_score desc, then price asc.
        """
        # Determine which platforms to search
        enabled = platforms
        if not enabled and profile:
            enabled = profile.enabled_platforms

        searchers = self.available_searchers(enabled)
        if not searchers:
            logger.warning("No searchers available")
            return []

        logger.info(
            "Searching %d platform(s): %s",
            len(searchers),
            ", ".join(s.name for s in searchers),
        )

        # --- Build the list of search queries ---
        # Primary query: brand + model (always)
        queries = [product.search_query()]

        # Secondary query: SKU or UPC (if product has identifiers)
        if product.has_identifiers():
            if product.sku:
                queries.append(product.sku)
                logger.info("Adding SKU search: %s", product.sku)
            if product.upc:
                queries.append(product.upc)
                logger.info("Adding UPC search: %s", product.upc)

        # AI query expansion (if enabled)
        if not no_expand:
            try:
                alt_queries = expand_queries(
                    brand=product.brand,
                    model=product.model,
                    category=product.category.value,
                    max_alternatives=3,
                )
                if alt_queries:
                    queries.extend(alt_queries)
                    logger.info("Added %d expanded queries", len(alt_queries))
            except Exception as e:
                logger.warning("Query expansion failed: %s", e)

        # --- Run all searches in parallel ---
        all_results: List[SearchResult] = []
        errors: Dict[str, str] = {}
        seen_urls: Set[str] = set()

        with ThreadPoolExecutor(
            max_workers=min(len(searchers) * len(queries), 4)
        ) as executor:
            futures = {}
            primary_query = queries[0] if queries else ""
            for searcher in searchers:
                for query in queries:
                    # Skip expanded queries on eBay — proxy product breaks
                    # the brand aspect filter, and it burns API quota
                    if (searcher.name == "ebay"
                            and query != primary_query
                            and not (product.sku and query == product.sku)
                            and not (product.upc and query == product.upc)):
                        continue
                    future = executor.submit(
                        self._search_single_query,
                        searcher,
                        product,
                        query,
                        max_results,
                    )
                    futures[future] = (searcher, query)

            for future in as_completed(futures):
                searcher, query = futures[future]
                try:
                    results = future.result()
                    # Deduplicate by URL
                    for r in results:
                        if r.url and r.url not in seen_urls:
                            seen_urls.add(r.url)
                            all_results.append(r)
                    logger.info(
                        "%s (q=%s) returned %d results",
                        searcher.name,
                        query[:30],
                        len(results),
                    )
                except Exception as e:
                    errors[searcher.name] = str(e)
                    logger.error(
                        "Search failed for %s (q=%s): %s",
                        searcher.name, query[:30], e,
                    )

        # --- Gender filtering ---
        # Determine the effective gender: explicit CLI flag takes priority,
        # then fall back to auto-detected gender from the product.
        effective_gender = None
        if gender_filter and gender_filter != "any":
            effective_gender = Gender(gender_filter)
        elif product.gender not in (Gender.UNKNOWN, Gender.UNISEX):
            effective_gender = product.gender

        if effective_gender:
            from .extractors.structured_data import _detect_gender_from_title
            pre_filter = len(all_results)
            filtered = []
            for r in all_results:
                result_gender = _detect_gender_from_title(r.title)
                # Keep results that match, are unisex, or are unknown gender
                if (result_gender == effective_gender
                        or result_gender == Gender.UNISEX
                        or result_gender == Gender.UNKNOWN):
                    filtered.append(r)
            all_results = filtered
            logger.info(
                "Gender filter (%s): %d -> %d results",
                effective_gender.value, pre_filter, len(all_results),
            )

        # --- Size filtering ---
        if size_strict and product.size and product.size.lower() != "unknown":
            target_size = _normalize_size(product.size)
            if target_size:
                pre_filter_size = len(all_results)
                filtered_by_size = []
                for r in all_results:
                    result_size = _normalize_size(r.size)
                    if _size_matches(target_size, result_size):
                        filtered_by_size.append(r)
                all_results = filtered_by_size
                logger.info(
                    "Size filter (strict=%s, target=%s): %d -> %d results",
                    size_strict, target_size,
                    pre_filter_size, len(all_results),
                )

        # Initial text-based scoring (used to rank candidates for vision)
        for result in all_results:
            result.match_score = score_match(product, result)

        # Apply user profile filters
        if profile:
            all_results = self._apply_filters(all_results, product, profile)

        # Sort by text score first (needed for vision to pick top candidates)
        all_results.sort(
            key=lambda r: (-r.match_score, r.price)
        )

        # --- Vision matching (if enabled) ---
        vision_scores: Dict[str, float] = {}
        if not no_vision and product.image_url and all_results:
            try:
                product_desc = f"{product.brand} {product.model}"
                vision_scores = score_visual_matches(
                    product_image_url=product.image_url,
                    product_description=product_desc,
                    results=all_results,
                    max_comparisons=10,
                )
                logger.info(
                    "Vision matching returned %d scores",
                    len(vision_scores),
                )
            except Exception as e:
                logger.warning("Vision matching failed: %s", e)

        # --- Comprehensive quality scoring ---
        all_results = _score_results(product, all_results, vision_scores)

        # --- Min score filter ---
        if min_score > 0:
            pre_filter_score = len(all_results)
            all_results = [r for r in all_results if r.match_score >= min_score]
            logger.info(
                "Min score filter (%d): %d -> %d results",
                min_score, pre_filter_score, len(all_results),
            )

        # Sort by score descending, then price ascending
        all_results.sort(key=lambda r: (-r.match_score, r.price))

        return all_results

    def _search_single_query(
        self,
        searcher: SearcherBase,
        product: Product,
        query: str,
        max_results: int,
    ) -> List[SearchResult]:
        """Run a single searcher with a specific query string.

        Creates a temporary Product copy with the query baked into brand+model
        so that the searcher's search_query() method returns our custom query.
        This allows SKU searches and expanded queries to flow through the
        existing searcher interface without modifying SearcherBase.
        """
        self._rate_limiter.wait(searcher.name)

        # If query matches the product's normal search query, use the product as-is
        if query == product.search_query():
            return searcher.search(product, max_results)

        # Create a lightweight product proxy with the override query
        from dataclasses import replace
        proxy = replace(product, brand=query, model="")
        return searcher.search(proxy, max_results)

    def _apply_filters(
        self,
        results: List[SearchResult],
        product: Product,
        profile: UserProfile,
    ) -> List[SearchResult]:
        """Apply user profile filters to results."""
        filtered = results

        # Max price filter
        if profile.max_price is not None:
            filtered = [
                r for r in filtered if r.price <= profile.max_price
            ]

        # Color strict filter
        if profile.color_strict and product.color.lower() != "unknown":
            filtered = [
                r for r in filtered
                if r.color.lower() == product.color.lower()
                or r.color.lower() == "unknown"
            ]

        return filtered
