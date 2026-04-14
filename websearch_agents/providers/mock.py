from __future__ import annotations

from collections.abc import Mapping

from .base import SearchProvider
from ..types import SearchResult


class MockProvider(SearchProvider):
    def __init__(self, results_by_query: Mapping[str, list[SearchResult]] | None = None):
        self.results_by_query = dict(results_by_query or {})
        self.calls: list[str] = []

    def search(self, query: str, limit: int = 5) -> list[SearchResult]:
        self.calls.append(query)
        results = self.results_by_query.get(query, self.results_by_query.get("*", []))
        return list(results[:limit])
