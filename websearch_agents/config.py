from __future__ import annotations

from dataclasses import dataclass
import os

DEFAULT_SEARXNG_URL = "http://localhost:8080"


@dataclass(slots=True)
class PipelineConfig:
    searxng_url: str | None = DEFAULT_SEARXNG_URL
    engine: str | None = None
    search_limit: int = 5
    max_evidence: int = 5
    request_timeout: float = 15.0
    user_agent: str = "viseer/0.1"
    weak_text_threshold: int = 400
    recovery_json_limit: int = 2

    @classmethod
    def from_env(cls) -> "PipelineConfig":
        return cls(
            searxng_url=os.getenv("SEARXNG_URL") or DEFAULT_SEARXNG_URL,
            engine=os.getenv("SEARXNG_ENGINE") or None,
            search_limit=int(os.getenv("SEARCH_LIMIT", "5")),
            max_evidence=int(os.getenv("MAX_EVIDENCE", "5")),
            request_timeout=float(os.getenv("REQUEST_TIMEOUT", "15")),
            user_agent=os.getenv("USER_AGENT", "viseer/0.1"),
            weak_text_threshold=int(os.getenv("WEAK_TEXT_THRESHOLD", "400")),
            recovery_json_limit=int(os.getenv("RECOVERY_JSON_LIMIT", "2")),
        )
