"""
Size normalization and comparison.

Handles the chaos of clothing sizes:
- Letter sizes: XS, S, M, L, XL, XXL, XXXL
- Numeric tops: 0, 2, 4, 6, 8, 10, 12, 14, 16
- Bottoms waist: 28, 29, 30, 31, 32, 33, 34, 36, 38, 40, 42
- Bottoms waist x inseam: 32x32, 34x30
- Shoe sizes: 6, 6.5, 7, 7.5 ... 14, 15 (US)
- One-size: OS, OSFA, one size
"""

import re
from typing import Optional

from ..models import Category


# ---------------------------------------------------------------------------
# Letter size ordering (index = relative size)
# ---------------------------------------------------------------------------

LETTER_SIZES = ["XXS", "XS", "S", "M", "L", "XL", "XXL", "XXXL", "4XL", "5XL"]

_LETTER_NORMALIZE = {
    "xxs": "XXS", "2xs": "XXS",
    "xs": "XS", "x-small": "XS", "extra small": "XS",
    "s": "S", "sm": "S", "small": "S",
    "m": "M", "md": "M", "med": "M", "medium": "M",
    "l": "L", "lg": "L", "large": "L",
    "xl": "XL", "x-large": "XL", "extra large": "XL",
    "xxl": "XXL", "2xl": "XXL", "xx-large": "XXL",
    "xxxl": "XXXL", "3xl": "XXXL", "xxx-large": "XXXL",
    "4xl": "4XL", "xxxxl": "4XL",
    "5xl": "5XL",
}

# Numeric women's tops -> letter mapping (approximate)
_NUMERIC_TO_LETTER = {
    "0": "XXS", "00": "XXS",
    "2": "XS",
    "4": "S",
    "6": "S",
    "8": "M",
    "10": "M",
    "12": "L",
    "14": "L",
    "16": "XL",
    "18": "XXL",
    "20": "XXXL",
}

# One-size patterns
_ONE_SIZE = {"os", "osfa", "one size", "one size fits all", "o/s"}

# Shoe size regex: matches 6, 6.5, 10, 10.5, etc.
_SHOE_SIZE_RE = re.compile(r"^(\d{1,2}(?:\.\d)?)\s*(?:us)?$", re.IGNORECASE)

# Waist x inseam regex: matches 32x32, 34x30, 32 x 32, etc.
_WAIST_INSEAM_RE = re.compile(
    r"^(\d{2})\s*[xX]\s*(\d{2})$"
)

# Plain waist size: 28-42
_WAIST_RE = re.compile(r"^(\d{2})$")

# Generic numeric pattern
_NUMERIC_RE = re.compile(r"^(\d+(?:\.\d+)?)$")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def normalize_size(raw: str, category: Category = Category.UNKNOWN) -> str:
    """Normalize a raw size string to a canonical form.

    Args:
        raw: The raw size string from a product listing.
        category: Product category for context-aware normalization.

    Returns:
        Normalized size string (e.g., "M", "32x32", "10.5").
    """
    if not raw:
        return "Unknown"

    clean = raw.strip().lower()

    # One size
    if clean in _ONE_SIZE:
        return "OS"

    # Letter sizes
    letter = _LETTER_NORMALIZE.get(clean)
    if letter:
        return letter

    # Category-specific handling
    if category == Category.SHOES:
        m = _SHOE_SIZE_RE.match(clean)
        if m:
            size_val = float(m.group(1))
            # Normalize: no trailing .0 for whole sizes
            if size_val == int(size_val):
                return str(int(size_val))
            return str(size_val)

    if category in (Category.BOTTOMS, Category.UNKNOWN):
        # Waist x inseam
        m = _WAIST_INSEAM_RE.match(clean)
        if m:
            return f"{m.group(1)}x{m.group(2)}"

        # Plain waist
        m = _WAIST_RE.match(clean)
        if m:
            waist = int(m.group(1))
            if 26 <= waist <= 50:
                return str(waist)

    if category == Category.TOPS:
        # Numeric women's/unisex top sizes
        letter = _NUMERIC_TO_LETTER.get(clean)
        if letter:
            return letter

    # Generic numeric (could be shoe, waist, etc.)
    m = _NUMERIC_RE.match(clean)
    if m:
        return m.group(1)

    # Last resort: return cleaned up
    return raw.strip().upper() if len(raw.strip()) <= 5 else raw.strip()


def sizes_match(
    size_a: str,
    size_b: str,
    category: Category = Category.UNKNOWN,
    fuzzy: bool = True,
) -> bool:
    """Check if two sizes match.

    Args:
        size_a: First size (normalized).
        size_b: Second size (normalized).
        category: Product category for context-aware comparison.
        fuzzy: If True, allows adjacent sizes (e.g., M matches S or L).

    Returns:
        True if sizes match (exact or fuzzy-adjacent).
    """
    a = normalize_size(size_a, category)
    b = normalize_size(size_b, category)

    # Exact match
    if a.lower() == b.lower():
        return True

    if not fuzzy:
        return False

    # Adjacent letter sizes
    a_upper = a.upper()
    b_upper = b.upper()
    if a_upper in LETTER_SIZES and b_upper in LETTER_SIZES:
        idx_a = LETTER_SIZES.index(a_upper)
        idx_b = LETTER_SIZES.index(b_upper)
        return abs(idx_a - idx_b) <= 1

    # Adjacent shoe sizes (within 0.5)
    if category == Category.SHOES:
        try:
            fa = float(a)
            fb = float(b)
            return abs(fa - fb) <= 0.5
        except ValueError:
            pass

    # Adjacent waist sizes (within 1 inch)
    if category in (Category.BOTTOMS, Category.UNKNOWN):
        # Handle waist x inseam
        wa = _extract_waist(a)
        wb = _extract_waist(b)
        if wa is not None and wb is not None:
            return abs(wa - wb) <= 1

    return False


def size_distance(
    size_a: str,
    size_b: str,
    category: Category = Category.UNKNOWN,
) -> int:
    """Return distance between two sizes. 0 = exact, 1 = adjacent, 99 = no match.

    Used by the scorer for weighted size matching.
    """
    a = normalize_size(size_a, category)
    b = normalize_size(size_b, category)

    if a.lower() == b.lower():
        return 0

    # Letter sizes
    a_upper = a.upper()
    b_upper = b.upper()
    if a_upper in LETTER_SIZES and b_upper in LETTER_SIZES:
        return abs(LETTER_SIZES.index(a_upper) - LETTER_SIZES.index(b_upper))

    # Shoe sizes
    if category == Category.SHOES:
        try:
            return int(abs(float(a) - float(b)) * 2)  # 0.5 = 1, 1.0 = 2
        except ValueError:
            pass

    # Waist sizes
    wa = _extract_waist(a)
    wb = _extract_waist(b)
    if wa is not None and wb is not None:
        return abs(wa - wb)

    return 99


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _extract_waist(size_str: str) -> Optional[int]:
    """Extract waist measurement from a size string."""
    m = _WAIST_INSEAM_RE.match(size_str)
    if m:
        return int(m.group(1))
    m = _WAIST_RE.match(size_str)
    if m:
        val = int(m.group(1))
        if 26 <= val <= 50:
            return val
    return None


def extract_size_from_text(text: str, category: Category = Category.UNKNOWN) -> str:
    """Try to extract a size from free-form text (title, description).

    Looks for common size patterns in the text and returns the first match.
    """
    if not text:
        return "Unknown"

    text_clean = text.strip()

    # One size
    for pattern in _ONE_SIZE:
        if pattern in text_clean.lower():
            return "OS"

    # Waist x inseam (32x32)
    m = _WAIST_INSEAM_RE.search(text_clean)
    if m:
        return f"{m.group(1)}x{m.group(2)}"

    # Full-word sizes first ("Large", "Medium", "Small", etc.)
    fullword_re = re.compile(
        r"\b(extra\s*small|x-small|small|medium|large|x-large|extra\s*large"
        r"|xx-large|xxx-large)\b",
        re.IGNORECASE
    )
    m = fullword_re.search(text_clean)
    if m:
        return normalize_size(m.group(1), category)

    # Letter sizes — look for isolated letter sizes in text
    letter_re = re.compile(
        r"\b(XXS|XS|XXXL|XXL|XL|[SML])\b",
        re.IGNORECASE
    )
    m = letter_re.search(text_clean)
    if m:
        return normalize_size(m.group(1), category)

    # Shoe sizes: "Size 10.5" or "US 10.5" or "sz 10.5"
    shoe_re = re.compile(
        r"(?:size|sz|us)\s*(\d{1,2}(?:\.\d)?)",
        re.IGNORECASE
    )
    m = shoe_re.search(text_clean)
    if m:
        return normalize_size(m.group(1), Category.SHOES)

    # Waist only
    waist_re = re.compile(r"\bW?(\d{2})\b")
    m = waist_re.search(text_clean)
    if m:
        val = int(m.group(1))
        if 26 <= val <= 50:
            return str(val)

    return "Unknown"
