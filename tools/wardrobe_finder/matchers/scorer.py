"""
Match confidence scorer.

Scores how well a SearchResult matches the target Product on a 0-100 scale:
- Brand match:  30 points (exact=30, fuzzy=15, none=0)
- Model match:  30 points (exact=30, partial=15, none=0)
- Size match:   25 points (exact=25, adjacent=10, none=0)
- Color match:  15 points (exact=15, similar=8, none=0)
"""

from ..models import Product, SearchResult
from .brand_aliases import normalize_brand, normalize_model, resolve_brand
from .size_converter import size_distance


# ---------------------------------------------------------------------------
# Weights
# ---------------------------------------------------------------------------

WEIGHT_BRAND = 30
WEIGHT_MODEL = 30
WEIGHT_SIZE = 25
WEIGHT_COLOR = 15

# ---------------------------------------------------------------------------
# Color similarity groups
# ---------------------------------------------------------------------------

COLOR_GROUPS = {
    "black": {"black", "noir", "jet", "onyx", "ebony", "charcoal"},
    "white": {"white", "blanc", "cream", "ivory", "off-white", "off white", "snow"},
    "grey": {"grey", "gray", "silver", "slate", "ash", "heather grey", "heather gray"},
    "blue": {"blue", "navy", "cobalt", "royal", "sky", "denim", "indigo", "teal"},
    "red": {"red", "crimson", "scarlet", "burgundy", "maroon", "cardinal", "wine"},
    "green": {"green", "olive", "sage", "forest", "moss", "emerald", "hunter", "army"},
    "brown": {"brown", "tan", "khaki", "camel", "cognac", "chocolate", "mocha", "beige"},
    "pink": {"pink", "rose", "blush", "salmon", "coral", "fuchsia", "magenta"},
    "orange": {"orange", "rust", "burnt orange", "terracotta", "copper"},
    "yellow": {"yellow", "gold", "mustard", "lemon"},
    "purple": {"purple", "violet", "plum", "lavender", "lilac", "mauve", "grape"},
}

# Build reverse lookup: color_word -> group_name
_COLOR_GROUP_LOOKUP: dict = {}
for group, words in COLOR_GROUPS.items():
    for word in words:
        _COLOR_GROUP_LOOKUP[word.lower()] = group


def _color_group(color: str) -> str:
    """Get the color group for a color string."""
    if not color:
        return ""
    c = color.strip().lower()
    return _COLOR_GROUP_LOOKUP.get(c, c)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def score_match(product: Product, result: SearchResult) -> int:
    """Score how well a SearchResult matches a Product.

    When the extractor can't determine size or color (Unknown/empty/None),
    those components are skipped and their points redistributed
    proportionally across the remaining components.

    Args:
        product: The target product extracted from retail URL.
        result: A listing from a resale marketplace.

    Returns:
        Score from 0-100.
    """
    # Determine which components have data
    has_size = bool(
        product.size
        and product.size.lower() != "unknown"
        and product.size.strip()
    )
    has_color = bool(
        product.color
        and product.color.lower() != "unknown"
        and product.color.strip()
    )

    # Calculate available weight (only components with data)
    available_weight = WEIGHT_BRAND + WEIGHT_MODEL
    if has_size:
        available_weight += WEIGHT_SIZE
    if has_color:
        available_weight += WEIGHT_COLOR

    # Score each component that has data
    raw_total = 0
    raw_total += _score_brand(product, result)
    raw_total += _score_model(product, result)
    if has_size:
        raw_total += _score_size(product, result)
    if has_color:
        raw_total += _score_color(product, result)

    # Normalize to 0-100 scale based on available components
    if available_weight == 0:
        return 0
    normalized = round(raw_total * 100 / available_weight)
    return min(normalized, 100)


# ---------------------------------------------------------------------------
# Scoring components
# ---------------------------------------------------------------------------

def _score_brand(product: Product, result: SearchResult) -> int:
    """Score brand match: exact=30, fuzzy=15, none=0."""
    p_brand = normalize_brand(product.brand).lower()
    r_brand_from_title = resolve_brand(result.title)

    if r_brand_from_title:
        r_brand = r_brand_from_title.lower()
        if r_brand == p_brand:
            return WEIGHT_BRAND
        # Fuzzy: brand appears somewhere in title
        if p_brand in result.title.lower():
            return WEIGHT_BRAND // 2
    else:
        # Check raw text
        if p_brand in result.title.lower():
            return WEIGHT_BRAND // 2

    return 0


def _score_model(product: Product, result: SearchResult) -> int:
    """Score model/style match: exact=30, partial=15, none=0."""
    p_model = normalize_model(product.model).lower()
    if not p_model or p_model == "unknown":
        # If no model specified, give partial credit if brand matches
        return 0

    r_title = result.title.lower()

    # Exact model name in title
    if p_model in r_title:
        return WEIGHT_MODEL

    # Check original (un-normalized) model name
    if product.model.lower() in r_title:
        return WEIGHT_MODEL

    # Partial: check individual words (at least half must match)
    model_words = p_model.split()
    if len(model_words) > 1:
        matched = sum(1 for w in model_words if w in r_title)
        if matched >= len(model_words) // 2:
            return WEIGHT_MODEL // 2

    return 0


def _score_size(product: Product, result: SearchResult) -> int:
    """Score size match: exact=25, adjacent=10, none=0."""
    if not product.size or product.size.lower() == "unknown":
        return 0
    if not result.size or result.size.lower() == "unknown":
        return 0

    dist = size_distance(product.size, result.size, product.category)

    if dist == 0:
        return WEIGHT_SIZE
    elif dist == 1:
        return 10
    elif dist == 2:
        return 5
    return 0


def _score_color(product: Product, result: SearchResult) -> int:
    """Score color match: exact=15, similar=8, none=0."""
    p_color = product.color.strip().lower() if product.color else ""
    r_color = result.color.strip().lower() if result.color else ""

    if not p_color or p_color == "unknown":
        return 0

    # Check result color field first, then fall back to title
    if not r_color or r_color == "unknown":
        # Try to find color in title
        r_color = result.title.lower()

    # Exact match
    if p_color == r_color:
        return WEIGHT_COLOR

    # Color in result text
    if p_color in r_color:
        return WEIGHT_COLOR

    # Same color group (e.g., "navy" and "blue" are similar)
    p_group = _color_group(p_color)
    r_group = _color_group(r_color)
    if p_group and r_group and p_group == r_group:
        return WEIGHT_COLOR // 2

    # Check if product color word appears in result title
    if p_color in result.title.lower():
        return WEIGHT_COLOR // 2

    return 0
