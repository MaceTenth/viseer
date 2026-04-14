from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class SearchResult:
    title: str
    url: str
    snippet: str = ""
    source: str = ""
    published_at: str | None = None
    score: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class PageDocument:
    url: str
    title: str
    text: str
    fetched_at: str
    published_at: str | None = None
    extraction_method: str = "unknown"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class Evidence:
    url: str
    title: str
    quote: str
    summary: str
    score: float
    published_at: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class Citation:
    title: str
    url: str
    quote: str = ""
    published_at: str | None = None
    accessed_at: str | None = None


@dataclass(slots=True)
class QueryTrace:
    query: str
    result_count: int
    urls: list[str] = field(default_factory=list)


@dataclass(slots=True)
class AnswerTrace:
    queries: list[QueryTrace] = field(default_factory=list)
    pages_fetched: int = 0
    pages_extracted: int = 0
    failures: list[dict[str, str]] = field(default_factory=list)


@dataclass(slots=True)
class Answer:
    question: str
    answer: str
    citations: list[Citation]
    evidence: list[Evidence]
    strategy: str
    metadata: dict[str, Any] = field(default_factory=dict)
    trace: AnswerTrace | None = None
