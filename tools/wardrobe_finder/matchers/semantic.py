"""
Rule-based query expansion for better marketplace matching.

Generates alternative search queries that a secondhand seller might use
when listing the same item. Uses brand aliases, model simplification,
and category-aware seller phrasing -- zero API calls, zero cost,
stdlib only.
"""

import logging
import re
from typing import List, Set

from .brand_aliases import (
    BRAND_ALIASES,
    MODEL_ALIASES,
    normalize_brand,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Filler words and style codes to strip from model names
# ---------------------------------------------------------------------------

_FILLER_WORDS: Set[str] = {
    "essential", "classic", "original", "premium", "basic",
    "standard", "vintage", "retro", "modern", "updated",
    "new", "iconic",
}

# Words that become orphaned when their qualifying word is stripped.
# "Classic Fit" -> strip "Classic" -> "Fit" alone is meaningless.
_ORPHAN_WORDS: Set[str] = {
    "fit", "edition", "series", "line", "style", "type", "cut",
}

# Regex: year codes like '07, '23, 2023, sub-model codes like LV8, SE, QS
_STYLE_CODE_RE = re.compile(
    r"""
    \s*'\d{2}\b            |  # Year shorthand: '07, '23
    \s*\b20\d{2}\b         |  # Full year: 2023, 2024
    \s*\b[A-Z][A-Z0-9]{1,3}\b   # Sub-model codes: LV8, SE, QS, GS, OG, V2
    """,
    re.VERBOSE,
)


# ---------------------------------------------------------------------------
# Category synonyms: how sellers actually title listings
# ---------------------------------------------------------------------------

_CATEGORY_SYNONYMS: dict = {
    # footwear
    "shoes": ["sneakers", "kicks", "shoes"],
    "sneakers": ["shoes", "kicks", "sneakers"],
    "boots": ["boots", "boot"],
    # tops
    "t-shirt": ["tee", "shirt", "top"],
    "shirt": ["top", "button down", "button up"],
    "hoodie": ["hoody", "pullover hoodie", "zip up hoodie"],
    "sweatshirt": ["crewneck", "crew neck", "pullover"],
    # bottoms
    "pants": ["trousers", "bottoms"],
    "sweatpants": ["sweats", "joggers", "sweatpant"],
    "sweatpant": ["sweats", "joggers", "sweatpants"],
    "joggers": ["sweats", "sweatpants", "jogger"],
    "jeans": ["denim", "jeans"],
    "shorts": ["short", "shorts"],
    # outerwear
    "jacket": ["coat", "outerwear"],
    "coat": ["jacket", "outerwear"],
    "vest": ["gilet", "puffer vest"],
    "puffer": ["puffer jacket", "down jacket", "puffer coat"],
    # dresses / skirts
    "dress": ["frock", "dress"],
    "skirt": ["mini skirt", "skirt"],
}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_brand_short_forms(canonical: str) -> List[str]:
    """Return short aliases for a canonical brand name.

    Picks aliases that are significantly shorter than the canonical name,
    which approximates abbreviations and common shorthand.
    """
    aliases = BRAND_ALIASES.get(canonical, [])
    threshold = max(len(canonical) * 0.6, 3)
    short = [a for a in aliases if len(a) < threshold and a.lower() != canonical.lower()]
    return short


def _get_brand_long_forms(canonical: str) -> List[str]:
    """Return longer or sub-brand aliases for a canonical brand name.

    Useful when the input is already a short form and we want to surface
    the fuller brand name that some sellers use (e.g. 'Polo Ralph Lauren').
    """
    aliases = BRAND_ALIASES.get(canonical, [])
    long = [
        a for a in aliases
        if len(a) > len(canonical) and a.lower() != canonical.lower()
    ]
    return long


def _simplify_model(model: str) -> str:
    """Strip filler words, orphan qualifiers, and style codes from a model name.

    'Essential Cinched Sweatpant' -> 'Cinched Sweatpant'
    'Air Force 1 '07 LV8'        -> 'Air Force 1'
    'Classic Fit Polo Shirt'      -> 'Polo Shirt'
    '501 Original Fit Jeans'      -> '501 Jeans'
    """
    # Strip style codes first (year shorthand, sub-model letters)
    simplified = _STYLE_CODE_RE.sub("", model).strip()

    # Strip filler words (case-insensitive, word boundary)
    words = simplified.split()
    filtered = [w for w in words if w.lower() not in _FILLER_WORDS]

    # Strip orphan words that only make sense after a filler
    # (e.g. "Fit" is only meaningful in "Classic Fit", not standalone)
    if filtered != words:
        # Something was removed -- check for orphaned qualifiers
        filtered = [w for w in filtered if w.lower() not in _ORPHAN_WORDS]

    simplified = " ".join(filtered) if filtered else simplified

    return simplified.strip()


def _get_model_aliases(model: str) -> List[str]:
    """Return known aliases for a model from MODEL_ALIASES.

    Checks both the canonical name and all alias lists.
    """
    model_lower = model.lower().strip()

    # Check if the model matches any canonical or alias entry
    for canonical, aliases in MODEL_ALIASES.items():
        all_forms = [canonical.lower()] + [a.lower() for a in aliases]
        if model_lower in all_forms:
            # Return forms that differ from the input
            results = []
            for form in [canonical] + aliases:
                if form.lower() != model_lower:
                    results.append(form)
            return results

    return []


def _detect_category_words(model: str, category: str) -> List[str]:
    """Find seller-phrasing synonyms for category words in the model name.

    Scans the model text and category for known category keywords, then
    returns alternative phrasings sellers commonly use.  Prefers longer
    (more specific) keyword matches to avoid substring false positives
    like "pants" matching inside "sweatpant".
    """
    combined = f"{model} {category}".lower()
    synonyms: List[str] = []
    matched_spans: List[range] = []

    # Sort keywords longest-first so "sweatpant" beats "pants"
    sorted_keywords = sorted(_CATEGORY_SYNONYMS.keys(), key=len, reverse=True)

    for keyword in sorted_keywords:
        # Find keyword in combined text
        idx = combined.find(keyword)
        if idx == -1:
            continue

        # Skip if this position was already claimed by a longer keyword
        span = range(idx, idx + len(keyword))
        if any(s.start <= idx < s.stop for s in matched_spans):
            continue

        matched_spans.append(span)

        for alt in _CATEGORY_SYNONYMS[keyword]:
            if alt.lower() not in combined:
                synonyms.append(alt)

    return synonyms


def _build_category_variant(brand_form: str, model: str, category: str) -> str:
    """Build a query replacing category words with seller synonyms.

    'Nike Essential Cinched Sweatpant' -> 'Nike Cinched Joggers'
    """
    simplified = _simplify_model(model)
    cat_synonyms = _detect_category_words(model, category)

    if not cat_synonyms:
        return ""

    # Replace the category word in the simplified model with first synonym
    # Sort longest-first to match "sweatpant" before "pants"
    result = simplified
    model_lower = simplified.lower()
    for keyword in sorted(_CATEGORY_SYNONYMS, key=len, reverse=True):
        if keyword in model_lower:
            # Case-insensitive replacement of the keyword
            pattern = re.compile(re.escape(keyword), re.IGNORECASE)
            result = pattern.sub(cat_synonyms[0], result, count=1)
            break

    query = f"{brand_form} {result}".strip()
    return query


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def expand_queries(
    brand: str,
    model: str,
    category: str = "clothing",
    max_alternatives: int = 3,
) -> List[str]:
    """Generate alternative search terms a resale seller might use.

    Uses rule-based expansion: brand aliases, model simplification,
    and category-aware seller phrasing. No API calls.

    Example:
        Input:  brand="Abercrombie & Fitch", model="Essential Cinched Sweatpant"
        Output: [
            "Abercrombie Cinched Sweatpant",
            "Abercrombie Cinched Joggers",
            "A&F Sweatpant",
        ]

    Args:
        brand: Product brand name.
        model: Product model/style name.
        category: Product category string.
        max_alternatives: Number of alternative queries to generate.

    Returns:
        List of alternative search query strings. May be empty if no
        meaningful alternatives can be constructed.
    """
    if not brand or not model:
        logger.debug("Missing brand or model, skipping query expansion")
        return []

    canonical_brand = normalize_brand(brand)
    primary = f"{canonical_brand} {model}".strip().lower()
    seen: Set[str] = {primary}
    results: List[str] = []

    def _add(query: str) -> bool:
        """Add query if distinct from what we already have."""
        normalized = query.strip()
        if not normalized:
            return False
        if normalized.lower() in seen:
            return False
        seen.add(normalized.lower())
        results.append(normalized)
        return True

    # ------------------------------------------------------------------
    # Strategy 1: Brand short form + simplified model
    # ------------------------------------------------------------------
    short_brands = _get_brand_short_forms(canonical_brand)
    simplified_model = _simplify_model(model)

    for sb in short_brands[:1]:  # Only best short form here; save slots
        if len(results) >= max_alternatives:
            break
        brand_display = sb.upper() if len(sb) <= 3 else sb.title()
        _add(f"{brand_display} {simplified_model}")

    # ------------------------------------------------------------------
    # Strategy 2: Canonical brand + simplified model (when model changed)
    # ------------------------------------------------------------------
    if simplified_model.lower() != model.lower():
        _add(f"{canonical_brand} {simplified_model}")

    # ------------------------------------------------------------------
    # Strategy 3: Known model aliases (highest signal -- "AF1", "chucks")
    # ------------------------------------------------------------------
    model_alts = _get_model_aliases(model)
    if simplified_model.lower() != model.lower():
        model_alts.extend(_get_model_aliases(simplified_model))

    # Prefer short aliases first (abbreviations like AF1, AJ1 are high value)
    model_alts.sort(key=len)

    # Strip brand prefix from model aliases to avoid "Adidas adidas superstar"
    brand_lower = canonical_brand.lower()
    cleaned_alts = []
    for alt in model_alts:
        alt_lower = alt.lower()
        if alt_lower.startswith(brand_lower + " "):
            stripped = alt[len(brand_lower):].strip()
            if stripped:
                cleaned_alts.append(stripped)
            # Still keep original form if it differs enough
            continue
        cleaned_alts.append(alt)
    # Deduplicate while preserving order
    seen_alts: Set[str] = set()
    unique_alts = []
    for a in cleaned_alts:
        if a.lower() not in seen_alts:
            seen_alts.add(a.lower())
            unique_alts.append(a)

    for alt_model in unique_alts:
        if len(results) >= max_alternatives:
            break
        _add(f"{canonical_brand} {alt_model}")
        # Also try short brand + model alias
        for sb in short_brands[:1]:
            if len(results) >= max_alternatives:
                break
            brand_display = sb.upper() if len(sb) <= 3 else sb.title()
            _add(f"{brand_display} {alt_model}")

    # ------------------------------------------------------------------
    # Strategy 4: Brand long-form variants (lower priority filler)
    # ------------------------------------------------------------------
    long_brands = _get_brand_long_forms(canonical_brand)
    for lb in long_brands:
        if len(results) >= max_alternatives:
            break
        _add(f"{lb.title()} {simplified_model}")

    # ------------------------------------------------------------------
    # Strategy 5: Category-aware seller phrasing
    # ------------------------------------------------------------------
    if len(results) < max_alternatives:
        # Try with canonical brand
        variant = _build_category_variant(canonical_brand, model, category)
        _add(variant)

    if len(results) < max_alternatives:
        # Try with short brand
        for sb in short_brands:
            if len(results) >= max_alternatives:
                break
            brand_display = sb.upper() if len(sb) <= 3 else sb.title()
            variant = _build_category_variant(brand_display, model, category)
            _add(variant)

    # ------------------------------------------------------------------
    # Strategy 6: Brand + category synonym as a short fallback
    # ------------------------------------------------------------------
    if len(results) < max_alternatives:
        cat_syns = _detect_category_words(model, category)
        for syn in cat_syns:
            if len(results) >= max_alternatives:
                break
            # Short brand + synonym is how many resale listings are titled
            brand_form = short_brands[0] if short_brands else canonical_brand
            brand_display = (
                brand_form.upper() if len(brand_form) <= 3
                else brand_form.title()
            )
            _add(f"{brand_display} {syn}")

    final = results[:max_alternatives]
    if final:
        logger.info(
            "Query expansion generated %d alternatives: %s", len(final), final
        )
    else:
        logger.debug("Query expansion produced no alternatives for %s %s", brand, model)

    return final
