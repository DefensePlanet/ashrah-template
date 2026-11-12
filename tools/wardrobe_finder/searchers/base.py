"""Base class for marketplace searchers.

CRITICAL: This interface is the contract between the coordinator and all
marketplace searchers. Bowser's Poshmark/Depop scrapers subclass this.
Do NOT change the method signatures without coordinating with all searcher
implementations.
"""

from abc import ABC, abstractmethod
from typing import List

from ..models import Product, SearchResult


class SearcherBase(ABC):
    """Base class for all marketplace searchers."""

    name: str = "unknown"

    @abstractmethod
    def search(self, product: Product, max_results: int = 20) -> List[SearchResult]:
        """Search this platform for the product. Returns list of SearchResult."""
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """Check if this searcher is operational (API key set, deps available, etc.)."""
        ...

    def __repr__(self):
        return f"<{self.__class__.__name__} name={self.name}>"
