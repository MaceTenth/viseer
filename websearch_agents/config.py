from __future__ import annotations

from dataclasses import dataclass
import os

DEFAULT_SEARXNG_URL = "http://localhost:8080"
DEFAULT_REDDIT_URL = "https://www.reddit.com"


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(slots=True)
class PipelineConfig:
    search_provider: str = "searxng"
    searxng_url: str | None = DEFAULT_SEARXNG_URL
    engine: str | None = None
    reddit_base_url: str = DEFAULT_REDDIT_URL
    reddit_subreddit: str | None = None
    reddit_sort: str = "relevance"
    reddit_time: str = "all"
    reddit_include_over_18: bool = False
    reddit_comment_limit: int = 8
    reddit_bearer_token: str | None = None
    search_limit: int = 5
    max_evidence: int = 5
    request_timeout: float = 15.0
    user_agent: str = "viseer/0.1"
    weak_text_threshold: int = 400
    recovery_json_limit: int = 2

    @classmethod
    def from_env(cls) -> "PipelineConfig":
        return cls(
            search_provider=os.getenv("SEARCH_PROVIDER", "searxng"),
            searxng_url=os.getenv("SEARXNG_URL") or DEFAULT_SEARXNG_URL,
            engine=os.getenv("SEARXNG_ENGINE") or None,
            reddit_base_url=os.getenv("REDDIT_BASE_URL") or DEFAULT_REDDIT_URL,
            reddit_subreddit=os.getenv("REDDIT_SUBREDDIT") or None,
            reddit_sort=os.getenv("REDDIT_SORT", "relevance"),
            reddit_time=os.getenv("REDDIT_TIME", "all"),
            reddit_include_over_18=_env_bool("REDDIT_INCLUDE_OVER_18"),
            reddit_comment_limit=int(os.getenv("REDDIT_COMMENT_LIMIT", "8")),
            reddit_bearer_token=os.getenv("REDDIT_BEARER_TOKEN") or None,
            search_limit=int(os.getenv("SEARCH_LIMIT", "5")),
            max_evidence=int(os.getenv("MAX_EVIDENCE", "5")),
            request_timeout=float(os.getenv("REQUEST_TIMEOUT", "15")),
            user_agent=os.getenv("USER_AGENT", "viseer/0.1"),
            weak_text_threshold=int(os.getenv("WEAK_TEXT_THRESHOLD", "400")),
            recovery_json_limit=int(os.getenv("RECOVERY_JSON_LIMIT", "2")),
        )
