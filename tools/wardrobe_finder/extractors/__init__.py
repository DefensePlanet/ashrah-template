"""Product extractors — pull structured product data from retail URLs."""

from .base import ExtractorBase
from .structured_data import StructuredDataExtractor

__all__ = ["ExtractorBase", "StructuredDataExtractor"]
