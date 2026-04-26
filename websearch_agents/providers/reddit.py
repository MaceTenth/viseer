from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
import html
import json
import re
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .base import SearchProvider
from ..types import SearchResult

REDDIT_SORTS = {"relevance", "hot", "top", "new", "comments"}
REDDIT_TIME_FILTERS = {"hour", "day", "week", "month", "year", "all"}

_SUBREDDIT_RE = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_]{0,20}$")


def _validate_choice(name: str, value: str, valid: set[str]) -> str:
    candidate = value.strip().lower()
    if candidate not in valid:
        options = ", ".join(sorted(valid))
        raise ValueError(f"Invalid Reddit {name} '{value}'. Valid options: {options}")
    return candidate


def _validate_subreddit(subreddit: str | None) -> str | None:
    if subreddit is None:
        return None
    candidate = subreddit.strip()
    if candidate.lower().startswith("r/"):
        candidate = candidate[2:]
    if not _SUBREDDIT_RE.fullmatch(candidate):
        raise ValueError("Invalid subreddit name")
    return candidate


def _listing_children(payload: dict[str, Any]) -> list[dict[str, Any]]:
    data = payload.get("data")
    if not isinstance(data, dict):
        return []
    children = data.get("children")
    if not isinstance(children, list):
        return []
    return [item for item in children if isinstance(item, dict)]


def _published_at(data: dict[str, Any]) -> str | None:
    value = data.get("created_utc")
    if not isinstance(value, int | float):
        return None
    return datetime.fromtimestamp(value, UTC).isoformat()


def _clean(value: Any) -> str:
    return " ".join(html.unescape(str(value or "")).split())


def _snippet(data: dict[str, Any]) -> str:
    selftext = _clean(data.get("selftext"))
    if selftext:
        return selftext[:500]

    parts = [
        f"r/{data.get('subreddit')}" if data.get("subreddit") else "",
        f"u/{data.get('author')}" if data.get("author") else "",
        f"{data.get('score')} points" if data.get("score") is not None else "",
        f"{data.get('num_comments')} comments" if data.get("num_comments") is not None else "",
    ]
    return " ".join(part for part in parts if part)


def _permalink(base_url: str, data: dict[str, Any]) -> str:
    permalink = str(data.get("permalink") or "")
    if permalink.startswith("http://") or permalink.startswith("https://"):
        return permalink
    return f"{base_url.rstrip('/')}{permalink}"


class RedditProvider(SearchProvider):
    def __init__(
        self,
        *,
        base_url: str = "https://www.reddit.com",
        subreddit: str | None = None,
        sort: str = "relevance",
        time_filter: str = "all",
        include_over_18: bool = False,
        timeout: float = 15.0,
        user_agent: str = "viseer/0.1",
        bearer_token: str | None = None,
        opener: Callable[..., Any] | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.subreddit = _validate_subreddit(subreddit)
        self.sort = _validate_choice("sort", sort, REDDIT_SORTS)
        self.time_filter = _validate_choice("time filter", time_filter, REDDIT_TIME_FILTERS)
        self.include_over_18 = include_over_18
        self.timeout = timeout
        self.user_agent = user_agent
        self.bearer_token = bearer_token
        self.opener = opener or urlopen

    def search(self, query: str, limit: int = 5) -> list[SearchResult]:
        if limit <= 0:
            return []
        request_limit = max(1, min(int(limit), 100))
        params = {
            "q": query,
            "limit": request_limit,
            "sort": self.sort,
            "t": self.time_filter,
            "type": "link",
            "raw_json": "1",
        }
        if self.subreddit:
            params["restrict_sr"] = "1"
            endpoint = f"/r/{self.subreddit}/search.json"
        else:
            endpoint = "/search.json"

        headers = {
            "User-Agent": self.user_agent,
            "Accept": "application/json",
        }
        if self.bearer_token:
            headers["Authorization"] = f"Bearer {self.bearer_token}"

        request = Request(
            f"{self.base_url}{endpoint}?{urlencode(params)}",
            headers=headers,
        )
        with self.opener(request, timeout=self.timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))

        results: list[SearchResult] = []
        for child in _listing_children(payload):
            data = child.get("data")
            if not isinstance(data, dict):
                continue
            if data.get("over_18") and not self.include_over_18:
                continue
            if not data.get("permalink"):
                continue

            subreddit = str(data.get("subreddit") or "")
            url = _permalink(self.base_url, data)
            original_url = str(data.get("url_overridden_by_dest") or data.get("url") or "")
            results.append(
                SearchResult(
                    title=_clean(data.get("title")),
                    url=url,
                    snippet=_snippet(data),
                    source=f"reddit:r/{subreddit}" if subreddit else "reddit",
                    published_at=_published_at(data),
                    score=float(data.get("score") or 0),
                    metadata={
                        "provider": "reddit",
                        "id": data.get("id"),
                        "name": data.get("name"),
                        "subreddit": subreddit,
                        "author": data.get("author"),
                        "score": data.get("score"),
                        "num_comments": data.get("num_comments"),
                        "upvote_ratio": data.get("upvote_ratio"),
                        "permalink": data.get("permalink"),
                        "original_url": original_url,
                        "over_18": bool(data.get("over_18")),
                    },
                )
            )
            if len(results) >= limit:
                break
        return results
