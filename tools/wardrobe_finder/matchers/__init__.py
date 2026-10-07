"""Matchers — brand aliases, size conversion, match scoring, and AI matching."""

from .brand_aliases import normalize_brand, normalize_model, resolve_brand
from .size_converter import normalize_size, sizes_match
from .scorer import score_match
from .semantic import expand_queries
from .vision import score_visual_matches

__all__ = [
    "normalize_brand", "normalize_model", "resolve_brand",
    "normalize_size", "sizes_match",
    "score_match",
    "expand_queries",
    "score_visual_matches",
]
