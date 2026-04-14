from __future__ import annotations

from abc import ABC, abstractmethod

from ..types import SearchResult


class SearchProvider(ABC):
    @abstractmethod
    def search(self, query: str, limit: int = 5) -> list[SearchResult]:
        raise NotImplementedError
