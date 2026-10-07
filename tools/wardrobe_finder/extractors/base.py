"""Base class for product extractors."""

from abc import ABC, abstractmethod
from typing import Optional

from ..models import Product


class ExtractorBase(ABC):
    """Base class for all product extractors.

    An extractor takes a retail URL and returns a Product with as many
    fields populated as possible.
    """

    name: str = "unknown"

    @abstractmethod
    def extract(self, url: str) -> Optional[Product]:
        """Extract product details from a retail URL.

        Returns a Product if extraction succeeded, None otherwise.
        """
        ...

    @abstractmethod
    def can_handle(self, url: str) -> bool:
        """Check if this extractor can handle the given URL."""
        ...

    def __repr__(self):
        return f"<{self.__class__.__name__} name={self.name}>"
