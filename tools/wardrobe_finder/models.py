"""
Data models for Wardrobe Finder.

Defines the core data structures used across all layers:
- Product: extracted from retail URLs
- SearchResult: individual marketplace listing
- UserProfile: stored size/color/platform preferences
- WatchEntry: a watched item for persistent monitoring
"""

from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, List
from enum import Enum


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class Category(Enum):
    TOPS = "tops"
    BOTTOMS = "bottoms"
    SHOES = "shoes"
    OUTERWEAR = "outerwear"
    ACCESSORIES = "accessories"
    DRESSES = "dresses"
    UNKNOWN = "unknown"


class Gender(Enum):
    MENS = "mens"
    WOMENS = "womens"
    UNISEX = "unisex"
    UNKNOWN = "unknown"


class Condition(Enum):
    NWT = "NWT"            # New with tags
    NWOT = "NWOT"          # New without tags
    LIKE_NEW = "Like New"
    GOOD = "Good"
    FAIR = "Fair"
    UNKNOWN = "Unknown"


# ---------------------------------------------------------------------------
# Core Data Models
# ---------------------------------------------------------------------------

@dataclass
class Product:
    """A product extracted from a retail URL."""
    brand: str
    model: str
    size: str               # Normalized size string
    color: str
    retail_price: float
    url: str
    category: Category
    gender: Gender = Gender.UNKNOWN
    image_url: Optional[str] = None
    description: Optional[str] = None
    sku: Optional[str] = None
    upc: Optional[str] = None       # UPC/EAN/GTIN barcode
    mpn: Optional[str] = None       # Manufacturer Part Number

    def to_dict(self) -> dict:
        d = asdict(self)
        d["category"] = self.category.value
        d["gender"] = self.gender.value
        return d

    def search_query(self) -> str:
        """Build a search query string from product details."""
        parts = [self.brand, self.model]
        parts = [p for p in parts if p and p.lower() != "unknown"]
        return " ".join(parts)

    def has_identifiers(self) -> bool:
        """Return True if this product has any machine-readable identifiers."""
        return bool(self.sku or self.upc or self.mpn)


@dataclass
class SearchResult:
    """A single listing from a resale marketplace."""
    platform: str
    title: str
    price: float
    size: str
    color: str
    condition: Condition
    url: str
    thumbnail: Optional[str] = None
    match_score: int = 0    # 0-100, filled by scorer

    def to_dict(self) -> dict:
        d = asdict(self)
        d["condition"] = self.condition.value
        return d


@dataclass
class UserProfile:
    """User preferences stored at ~/.wardrobe/profile.yaml."""
    sizes: Dict[str, str] = field(default_factory=dict)  # category_name -> size
    color_strict: bool = False
    max_price: Optional[float] = None
    enabled_platforms: List[str] = field(default_factory=lambda: [
        "ebay", "poshmark", "depop", "mercari", "thredup", "grailed"
    ])

    def get_size(self, category: Category) -> Optional[str]:
        """Get the user's size for a given category."""
        return self.sizes.get(category.value)

    def to_dict(self) -> dict:
        return {
            "sizes": self.sizes,
            "color_strict": self.color_strict,
            "max_price": self.max_price,
            "enabled_platforms": self.enabled_platforms,
        }


# ---------------------------------------------------------------------------
# Watch Entry (Phase 1.0.0 — Persistent Watching)
# ---------------------------------------------------------------------------

@dataclass
class WatchEntry:
    """A watched item for persistent monitoring."""
    id: str                                     # slug like "af1-white-10.5"
    name: str                                   # display name
    url: str                                    # original retail URL
    product: dict                               # Product.to_dict() snapshot
    max_price: Optional[float] = None
    platforms: Optional[List[str]] = None       # None = use profile defaults
    added: str = ""                             # ISO timestamp
    last_checked: Optional[str] = None
    check_count: int = 0

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# Condition parser
# ---------------------------------------------------------------------------

def parse_condition(text: str) -> Condition:
    """Extract condition from listing text using keyword matching."""
    if not text:
        return Condition.UNKNOWN
    text_lower = text.lower()
    if any(k in text_lower for k in ["nwt", "new with tags", "brand new with tags"]):
        return Condition.NWT
    if any(k in text_lower for k in ["nwot", "new without tags"]):
        return Condition.NWOT
    if any(k in text_lower for k in ["like new", "excellent", "mint", "pristine"]):
        return Condition.LIKE_NEW
    if any(k in text_lower for k in [
        "good condition", "gently used", "great condition", "lightly worn"
    ]):
        return Condition.GOOD
    if any(k in text_lower for k in ["fair", "used", "worn", "some wear", "well worn"]):
        return Condition.FAIR
    return Condition.UNKNOWN
