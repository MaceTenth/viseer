from __future__ import annotations

from datetime import UTC, datetime
import re
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from .types import Evidence, PageDocument, SearchResult

TRUSTED_HOSTS = {
    ".gov": 2.0,
    ".edu": 1.5,
}

PENALIZED_HOSTS = {
    "pinterest.com": -1.0,
}

TRACKING_PARAMS = {"fbclid", "gclid", "ref", "source"}


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def normalize_url(url: str) -> str:
    parsed = urlparse(url)
    query_items = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if not key.lower().startswith("utm_") and key.lower() not in TRACKING_PARAMS
    ]
    normalized = parsed._replace(
        scheme=parsed.scheme.lower(),
        netloc=parsed.netloc.lower(),
        path=parsed.path.rstrip("/") or "/",
        query=urlencode(sorted(query_items)),
        fragment="",
    )
    return urlunparse(normalized)


def dedupe_search_results(results: list[SearchResult]) -> list[SearchResult]:
    deduped: list[SearchResult] = []
    seen: set[str] = set()
    for result in results:
        key = normalize_url(result.url)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(result)
    return deduped


def domain_bonus(url: str) -> float:
    hostname = urlparse(url).netloc.lower()
    for suffix, bonus in TRUSTED_HOSTS.items():
        if hostname.endswith(suffix):
            return bonus
    for host, penalty in PENALIZED_HOSTS.items():
        if hostname == host or hostname.endswith(f".{host}"):
            return penalty
    return 0.0


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None

    candidate = value.strip()
    if not candidate:
        return None

    if candidate.endswith("Z"):
        candidate = candidate[:-1] + "+00:00"

    for parser in (
        lambda item: datetime.fromisoformat(item),
        lambda item: datetime.strptime(item, "%Y-%m-%d"),
        lambda item: datetime.strptime(item, "%Y/%m/%d"),
    ):
        try:
            parsed = parser(candidate)
            if parsed.tzinfo is None:
                return parsed.replace(tzinfo=UTC)
            return parsed.astimezone(UTC)
        except ValueError:
            continue
    return None


def recency_bonus(published_at: str | None, now: datetime | None = None) -> float:
    published = _parse_datetime(published_at)
    if published is None:
        return 0.0

    now = now or datetime.now(UTC)
    age_days = max((now - published).days, 0)
    if age_days <= 7:
        return 1.5
    if age_days <= 30:
        return 1.0
    if age_days <= 180:
        return 0.5
    return 0.0


def _split_sentences(text: str) -> list[str]:
    chunks = re.split(r"(?<=[.!?])\s+", text)
    return [chunk.strip() for chunk in chunks if chunk.strip()]


def _best_quote(question: str, text: str) -> str:
    question_terms = set(_tokenize(question))
    sentences = _split_sentences(text)[:12]
    if not sentences:
        return text[:240].strip()

    best_sentence = sentences[0]
    best_score = -1
    for sentence in sentences:
        sentence_terms = set(_tokenize(sentence))
        score = len(question_terms & sentence_terms)
        if score > best_score:
            best_score = score
            best_sentence = sentence
    return best_sentence[:240].strip()


def _summary(text: str) -> str:
    pieces = _split_sentences(text)[:2]
    if not pieces:
        return text[:280].strip()
    return " ".join(pieces)[:280].strip()


def rank_documents(
    question: str,
    docs: list[PageDocument],
    recency_weight: float = 0.0,
) -> list[Evidence]:
    question_terms = set(_tokenize(question))
    ranked: list[Evidence] = []

    for doc in docs:
        content = " ".join(part for part in (doc.title, doc.text) if part).strip()
        doc_terms = set(_tokenize(content))
        overlap = float(len(question_terms & doc_terms))
        quote = _best_quote(question, content)
        score = overlap + domain_bonus(doc.url) + (recency_weight * recency_bonus(doc.published_at))

        ranked.append(
            Evidence(
                url=doc.url,
                title=doc.title or doc.url,
                quote=quote,
                summary=_summary(content),
                score=score,
                published_at=doc.published_at,
                metadata={**doc.metadata, "extraction_method": doc.extraction_method},
            )
        )

    return sorted(ranked, key=lambda item: item.score, reverse=True)
