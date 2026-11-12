"""
Brand and model name normalization.

Maps common abbreviations, alternate spellings, and shorthand to canonical
brand/model names for consistent matching across marketplace listings.
"""

import re
from typing import Optional

# ---------------------------------------------------------------------------
# Brand alias map: canonical_name -> [aliases]
# All aliases stored lowercase for comparison.
# ---------------------------------------------------------------------------

BRAND_ALIASES: dict = {
    "Nike": [
        "nike", "nike inc", "nike inc.", "nike sportswear",
    ],
    "Adidas": [
        "adidas", "adidas originals", "adidas performance",
        "adidas sportswear", "adidas athletics",
    ],
    "Jordan": [
        "jordan", "air jordan", "jordan brand", "nike jordan",
    ],
    "New Balance": [
        "new balance", "nb", "new balance athletics",
    ],
    "Levi's": [
        "levis", "levi's", "levi strauss", "levi strauss & co",
        "levi strauss & co.", "levi's strauss",
    ],
    "Ralph Lauren": [
        "ralph lauren", "polo ralph lauren", "polo rl",
        "lauren ralph lauren", "rl",
    ],
    "Tommy Hilfiger": [
        "tommy hilfiger", "tommy", "tommy jeans", "hilfiger",
    ],
    "Calvin Klein": [
        "calvin klein", "ck", "calvin klein jeans", "ck jeans",
    ],
    "Carhartt": [
        "carhartt", "carhartt wip", "carhartt work in progress",
    ],
    "The North Face": [
        "the north face", "north face", "tnf",
    ],
    "Patagonia": [
        "patagonia",
    ],
    "Zara": [
        "zara", "zara man", "zara woman", "zara basic",
    ],
    "H&M": [
        "h&m", "h and m", "h & m", "hm", "hennes & mauritz",
    ],
    "Uniqlo": [
        "uniqlo", "uniqlo u",
    ],
    "Gap": [
        "gap", "gap inc", "gap factory",
    ],
    "Converse": [
        "converse", "converse all star",
    ],
    "Vans": [
        "vans", "vans off the wall",
    ],
    "Puma": [
        "puma", "puma sportswear",
    ],
    "Reebok": [
        "reebok", "reebok classic",
    ],
    "ASICS": [
        "asics", "asics tiger",
    ],
    "Under Armour": [
        "under armour", "ua", "under armor",
    ],
    "Champion": [
        "champion", "champion usa", "champion athleticwear",
    ],
    "Stussy": [
        "stussy", "stuessy", "stu\u0308ssy",
    ],
    "Supreme": [
        "supreme", "supreme nyc", "supreme new york",
    ],
    "Gucci": [
        "gucci",
    ],
    "Louis Vuitton": [
        "louis vuitton", "lv",
    ],
    "Balenciaga": [
        "balenciaga",
    ],
    "Prada": [
        "prada",
    ],
    "Burberry": [
        "burberry", "burberry london",
    ],
    "Versace": [
        "versace", "gianni versace",
    ],
    "Off-White": [
        "off-white", "off white", "offwhite",
    ],
    "A Bathing Ape": [
        "a bathing ape", "bape", "bathing ape",
    ],
}

# Build reverse lookup: lowercase alias -> canonical brand
_ALIAS_LOOKUP: dict = {}
for canonical, aliases in BRAND_ALIASES.items():
    _ALIAS_LOOKUP[canonical.lower()] = canonical
    for alias in aliases:
        _ALIAS_LOOKUP[alias.lower()] = canonical

# ---------------------------------------------------------------------------
# Model/style alias map: canonical_name -> [aliases]
# ---------------------------------------------------------------------------

MODEL_ALIASES: dict = {
    "Air Force 1": [
        "air force 1", "af1", "air force one", "air force 1 '07",
        "af1 07", "air force 1 07", "air force 1 low",
        "air force 1 high", "air force 1 mid",
    ],
    "Air Max 1": [
        "air max 1", "airmax 1", "am1",
    ],
    "Air Max 90": [
        "air max 90", "airmax 90", "am90",
    ],
    "Air Max 97": [
        "air max 97", "airmax 97", "am97",
    ],
    "Air Jordan 1": [
        "air jordan 1", "aj1", "jordan 1",
    ],
    "Air Jordan 4": [
        "air jordan 4", "aj4", "jordan 4",
    ],
    "Dunk Low": [
        "dunk low", "dunk lo", "sb dunk low", "nike dunk low",
    ],
    "Dunk High": [
        "dunk high", "dunk hi", "sb dunk high", "nike dunk high",
    ],
    "Stan Smith": [
        "stan smith", "stansmith",
    ],
    "Superstar": [
        "superstar", "adidas superstar", "shell toe", "shelltoe",
    ],
    "Ultraboost": [
        "ultraboost", "ultra boost", "ub",
    ],
    "990": [
        "990", "990v5", "990v6", "new balance 990",
    ],
    "550": [
        "550", "bb550", "new balance 550",
    ],
    "574": [
        "574", "new balance 574",
    ],
    "Chuck Taylor": [
        "chuck taylor", "chuck 70", "chucks", "all star",
        "chuck taylor all star",
    ],
    "Old Skool": [
        "old skool", "old school", "vans old skool",
    ],
    "501": [
        "501", "levis 501", "levi's 501", "501 original",
    ],
    "511": [
        "511", "levis 511", "levi's 511", "511 slim",
    ],
    "Nuptse": [
        "nuptse", "nuptse jacket", "nuptse vest", "1996 nuptse",
        "1996 retro nuptse",
    ],
}

_MODEL_LOOKUP: dict = {}
for canonical, aliases in MODEL_ALIASES.items():
    _MODEL_LOOKUP[canonical.lower()] = canonical
    for alias in aliases:
        _MODEL_LOOKUP[alias.lower()] = canonical


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def normalize_brand(raw: str) -> str:
    """Normalize a brand name to its canonical form.

    Returns the canonical brand name if found in aliases,
    otherwise returns the input with title-casing applied.
    """
    if not raw:
        return "Unknown"
    clean = raw.strip()
    canonical = _ALIAS_LOOKUP.get(clean.lower())
    if canonical:
        return canonical
    # Return as-is with basic title casing
    return clean.title() if clean.islower() else clean


def normalize_model(raw: str) -> str:
    """Normalize a model/style name to its canonical form.

    Returns the canonical model name if found in aliases,
    otherwise returns the input cleaned up.
    """
    if not raw:
        return ""
    clean = raw.strip()
    canonical = _MODEL_LOOKUP.get(clean.lower())
    if canonical:
        return canonical
    return clean


def resolve_brand(text: str) -> Optional[str]:
    """Try to find a known brand name in a text string.

    Checks longest aliases first to prefer specific matches.
    Uses word-boundary regex to avoid false positives from substring
    matching (e.g., "gap" matching inside "gaping").
    Returns canonical brand name or None.
    """
    if not text:
        return None
    text_lower = text.lower()
    # Sort aliases by length descending so longer matches win
    sorted_aliases = sorted(_ALIAS_LOOKUP.keys(), key=len, reverse=True)
    for alias in sorted_aliases:
        if re.search(r'\b' + re.escape(alias) + r'\b', text_lower):
            return _ALIAS_LOOKUP[alias]
    return None
