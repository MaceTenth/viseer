from __future__ import annotations

import json
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .base import SearchProvider
from ..types import SearchResult


def _extract_published_at(item: dict) -> str | None:
    for key in ("publishedDate", "published_at", "published", "date"):
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


class SearxngProvider(SearchProvider):
    def __init__(
        self,
        base_url: str,
        engine: str | None = None,
        timeout: float = 15.0,
        user_agent: str = "viseer/0.1",
    ):
        self.base_url = base_url.rstrip("/")
        self.engine = engine
        self.timeout = timeout
        self.user_agent = user_agent

    def search(self, query: str, limit: int = 5) -> list[SearchResult]:
        params = {"q": query, "format": "json"}
        if self.engine:
            params["engines"] = self.engine

        request = Request(
            f"{self.base_url}/search?{urlencode(params)}",
            headers={"User-Agent": self.user_agent},
        )
        with urlopen(request, timeout=self.timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))

        results: list[SearchResult] = []
        for item in payload.get("results", [])[:limit]:
            source = item.get("engine") or item.get("engines") or "searxng"
            if isinstance(source, list):
                source = ",".join(str(part) for part in source)

            results.append(
                SearchResult(
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    snippet=item.get("content", ""),
                    source=str(source),
                    published_at=_extract_published_at(item),
                    metadata=item,
                )
            )
        return results
