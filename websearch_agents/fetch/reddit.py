from __future__ import annotations

from collections.abc import Callable
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse
from urllib.request import Request, urlopen

from .http_fetcher import HttpFetcher

TRACKING_PARAMS = {"fbclid", "gclid", "ref", "source"}

REDDIT_HOSTS = {
    "reddit.com",
    "www.reddit.com",
    "old.reddit.com",
    "new.reddit.com",
    "np.reddit.com",
    "m.reddit.com",
}


def is_reddit_url(url: str) -> bool:
    hostname = (urlparse(url).hostname or "").lower()
    return hostname in REDDIT_HOSTS


def is_reddit_thread_url(url: str) -> bool:
    parsed = urlparse(url)
    return is_reddit_url(url) and "/comments/" in parsed.path


def reddit_thread_json_url(
    url: str,
    *,
    comment_limit: int = 8,
    comment_sort: str = "confidence",
) -> str:
    parsed = urlparse(url)
    path = parsed.path.rstrip("/")
    if not path.endswith(".json"):
        path = f"{path}.json"

    query = {
        key: value
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if not key.lower().startswith("utm_") and key.lower() not in TRACKING_PARAMS
    }
    query["raw_json"] = "1"
    query["limit"] = str(max(0, comment_limit))
    query["sort"] = comment_sort

    return urlunparse(
        parsed._replace(
            netloc="www.reddit.com",
            path=path,
            query=urlencode(sorted(query.items())),
            fragment="",
        )
    )


class RedditThreadFetcher(HttpFetcher):
    def __init__(
        self,
        timeout: float = 20.0,
        user_agent: str = "viseer/0.1",
        *,
        comment_limit: int = 8,
        comment_sort: str = "confidence",
        bearer_token: str | None = None,
        opener: Callable[..., Any] | None = None,
    ):
        super().__init__(timeout=timeout, user_agent=user_agent)
        self.comment_limit = comment_limit
        self.comment_sort = comment_sort
        self.bearer_token = bearer_token
        self.opener = opener or urlopen

    def fetch(self, url: str) -> str:
        if not is_reddit_thread_url(url):
            return super().fetch(url)

        request_url = reddit_thread_json_url(
            url,
            comment_limit=self.comment_limit,
            comment_sort=self.comment_sort,
        )
        headers = {
            "User-Agent": self.user_agent,
            "Accept": "application/json",
        }
        if self.bearer_token:
            headers["Authorization"] = f"Bearer {self.bearer_token}"

        request = Request(request_url, headers=headers)
        with self.opener(request, timeout=self.timeout) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            return response.read().decode(charset, errors="replace")
