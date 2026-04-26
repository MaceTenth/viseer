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

SOCIAL_HOSTS = {
    "linkedin.com",
    "x.com",
    "twitter.com",
    "facebook.com",
    "instagram.com",
    "youtube.com",
    "youtu.be",
    "tiktok.com",
    "threads.net",
}

COMMUNITY_HOSTS = {
    "reddit.com",
    "quora.com",
    "stackoverflow.com",
    "stackexchange.com",
    "news.ycombinator.com",
}

MARKETPLACE_HOSTS = {
    "amazon.com",
    "ebay.com",
    "etsy.com",
    "aliexpress.com",
    "mercari.com",
}

REFERENCE_HOSTS = {
    "wikipedia.org",
    "britannica.com",
}

GENERIC_HOST_LABELS = {
    "www",
    "m",
    "amp",
    "help",
    "support",
    "docs",
    "developers",
    "developer",
    "platform",
    "api",
    "blog",
    "news",
    "app",
    "web",
}

DOC_HINTS = ("docs", "developer", "developers", "api", "reference")
HELP_HINTS = ("help", "support", "faq", "kb", "article", "articles")
PRICING_HINTS = ("pricing", "price", "plans", "billing", "subscription")

GENERIC_QUERY_TERMS = {
    "a",
    "an",
    "and",
    "anti",
    "answer",
    "answers",
    "api",
    "ceo",
    "claim",
    "compare",
    "comparison",
    "cost",
    "current",
    "did",
    "direct",
    "docs",
    "founded",
    "founder",
    "help",
    "how",
    "info",
    "information",
    "is",
    "latest",
    "lookup",
    "official",
    "of",
    "on",
    "page",
    "pages",
    "price",
    "prices",
    "pricing",
    "question",
    "site",
    "statement",
    "the",
    "to",
    "today",
    "verify",
    "versus",
    "vs",
    "what",
    "who",
    "with",
}

MULTIPART_SUFFIXES = {
    "co.uk",
    "org.uk",
    "ac.uk",
    "com.au",
    "co.il",
    "co.jp",
    "com.br",
    "com.mx",
    "com.tr",
}

TRACKING_PARAMS = {"fbclid", "gclid", "ref", "source"}


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def _host_matches(hostname: str, candidates: set[str]) -> bool:
    return any(hostname == item or hostname.endswith(f".{item}") for item in candidates)


def _domain_family(hostname: str) -> str:
    parts = [part for part in hostname.lower().split(".") if part]
    if len(parts) <= 2:
        return ".".join(parts)

    last_two = ".".join(parts[-2:])
    if last_two in MULTIPART_SUFFIXES:
        return ".".join(parts[-3:])

    if len(parts) >= 3:
        last_three = ".".join(parts[-3:])
        suffix = ".".join(parts[-2:])
        if suffix in {"co.uk", "org.uk", "ac.uk", "co.il"}:
            return last_three
    return last_two


def _family_tokens(hostname: str) -> set[str]:
    family = _domain_family(hostname)
    parts = family.split(".")
    if len(parts) >= 2:
        labels = parts[:-1]
    else:
        labels = parts
    return set(_tokenize(" ".join(labels)))


def _host_tokens(hostname: str) -> set[str]:
    labels = [part for part in hostname.lower().split(".") if part]
    meaningful = [label for label in labels if label not in GENERIC_HOST_LABELS]
    return set(_tokenize(" ".join(meaningful)))


def _query_focus_terms(question: str) -> set[str]:
    return {
        token
        for token in _tokenize(question)
        if token not in GENERIC_QUERY_TERMS and (len(token) > 2 or token.isdigit())
    }


def _path_labels(url: str) -> set[str]:
    parsed = urlparse(url)
    path = parsed.path.lower()
    labels: set[str] = set()
    if any(hint in parsed.netloc.lower() or f"/{hint}" in path for hint in DOC_HINTS):
        labels.add("docs")
    if any(hint in parsed.netloc.lower() or f"/{hint}" in path for hint in HELP_HINTS):
        labels.add("help")
    if any(f"/{hint}" in path for hint in PRICING_HINTS):
        labels.add("pricing")
    return labels


def discover_preferred_domain_families(question: str, results: list[SearchResult]) -> set[str]:
    focus_terms = _query_focus_terms(question)
    if not focus_terms:
        return set()

    scores: dict[str, float] = {}
    for result in results:
        hostname = urlparse(result.url).netloc.lower()
        if not hostname:
            continue
        if _host_matches(hostname, SOCIAL_HOSTS | COMMUNITY_HOSTS | MARKETPLACE_HOSTS):
            continue

        family = _domain_family(hostname)
        family_terms = _family_tokens(hostname) | _host_tokens(hostname)
        title_terms = set(_tokenize(result.title))
        snippet_terms = set(_tokenize(result.snippet))
        overlap = focus_terms & family_terms
        if not overlap:
            continue

        score = 2.0 * len(overlap)
        if focus_terms & title_terms:
            score += 0.75
        if focus_terms & snippet_terms:
            score += 0.5
        if "official" in result.title.lower() or "official" in result.snippet.lower():
            score += 0.75
        score += 0.5 * len(_path_labels(result.url))
        if urlparse(result.url).path in {"", "/"}:
            score += 0.25
        scores[family] = scores.get(family, 0.0) + score

    ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    return {family for family, score in ranked[:4] if score >= 2.0}


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


def infer_source_profile(
    question: str,
    url: str,
    title: str,
    *,
    preferred_domain_families: set[str] | None = None,
) -> dict[str, object]:
    hostname = urlparse(url).netloc.lower()
    family = _domain_family(hostname)
    source_types: set[str] = set()
    reasons: list[str] = []
    preferred_domain_families = preferred_domain_families or set()

    if _host_matches(hostname, SOCIAL_HOSTS):
        source_types.add("social")
    if _host_matches(hostname, COMMUNITY_HOSTS):
        source_types.add("community")
    if _host_matches(hostname, MARKETPLACE_HOSTS):
        source_types.add("marketplace")
    if _host_matches(hostname, REFERENCE_HOSTS):
        source_types.add("reference")
    if domain_bonus(url) > 0:
        source_types.add("institutional")

    source_types |= _path_labels(url)
    if family in preferred_domain_families and "social" not in source_types and "marketplace" not in source_types:
        source_types.add("official")
        reasons.append("likely first-party domain")
    else:
        focus_terms = _query_focus_terms(question)
        if focus_terms & _family_tokens(hostname) and "social" not in source_types and "marketplace" not in source_types:
            source_types.add("entity_match")
            reasons.append("domain matches query entity")

    if "docs" in source_types:
        reasons.append("documentation-style page")
    if "help" in source_types:
        reasons.append("help/support page")
    if "pricing" in source_types:
        reasons.append("pricing/billing page")
    if "institutional" in source_types:
        reasons.append("institutional domain")
    if "social" in source_types:
        reasons.append("social/profile page")
    if "marketplace" in source_types:
        reasons.append("marketplace listing")
    if "reference" in source_types:
        reasons.append("reference source")

    return {
        "domain_family": family,
        "source_types": sorted(source_types),
        "reasons": reasons,
    }


def _strategy_source_bonus(strategy_name: str, source_types: set[str]) -> tuple[float, list[str]]:
    score = 0.0
    reasons: list[str] = []

    def add(condition: bool, value: float, reason: str) -> None:
        nonlocal score
        if condition and value:
            score += value
            reasons.append(reason)

    add("official" in source_types, {
        "direct_lookup": 2.0,
        "latest_info": 2.0,
        "verify_claim": 1.0,
        "compare_entities": 2.5,
        "price_validation": 3.0,
        "community_discussion": 0.25,
    }.get(strategy_name, 1.5), "official-domain boost")

    add("entity_match" in source_types, 0.75, "entity-domain match")
    add("docs" in source_types, {
        "compare_entities": 1.0,
        "price_validation": 0.5,
        "verify_claim": 0.5,
    }.get(strategy_name, 0.25), "docs-page boost")
    add("help" in source_types, {
        "price_validation": 1.0,
        "latest_info": 0.5,
        "compare_entities": 0.5,
    }.get(strategy_name, 0.25), "help-page boost")
    add("pricing" in source_types, {
        "price_validation": 1.5,
        "compare_entities": 1.25,
    }.get(strategy_name, 0.25), "pricing-page boost")
    add("institutional" in source_types, {
        "verify_claim": 1.5,
        "latest_info": 0.5,
    }.get(strategy_name, 0.25), "institutional-domain boost")

    add("social" in source_types, {
        "latest_info": -1.75,
        "compare_entities": -1.5,
        "price_validation": -2.0,
        "verify_claim": -1.5,
        "community_discussion": -0.25,
    }.get(strategy_name, -1.0), "social-source penalty")
    add("community" in source_types, {
        "latest_info": -1.25,
        "verify_claim": -1.0,
        "price_validation": -1.25,
        "community_discussion": 1.5,
    }.get(strategy_name, -0.75), "community-source signal")
    add("marketplace" in source_types, {
        "price_validation": -1.5,
        "compare_entities": -0.75,
    }.get(strategy_name, -0.5), "marketplace penalty")
    return score, reasons


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
    *,
    strategy_name: str = "direct_lookup",
    preferred_domain_families: set[str] | None = None,
) -> list[Evidence]:
    question_terms = set(_tokenize(question))
    ranked: list[Evidence] = []

    for doc in docs:
        content = " ".join(part for part in (doc.title, doc.text) if part).strip()
        doc_terms = set(_tokenize(content))
        overlap = float(len(question_terms & doc_terms))
        quote = _best_quote(question, content)
        source_profile = infer_source_profile(
            question,
            doc.url,
            doc.title or doc.url,
            preferred_domain_families=preferred_domain_families,
        )
        source_types = set(source_profile["source_types"])
        source_bonus, source_reasons = _strategy_source_bonus(strategy_name, source_types)
        recency_value = recency_weight * recency_bonus(doc.published_at)
        score = overlap + domain_bonus(doc.url) + recency_value + source_bonus
        ranking_reasons: list[str] = []
        if overlap:
            ranking_reasons.append(f"term overlap ({int(overlap)})")
        ranking_reasons.extend(source_profile["reasons"])
        ranking_reasons.extend(source_reasons)
        if recency_value > 0:
            ranking_reasons.append("recent source")

        ranked.append(
            Evidence(
                url=doc.url,
                title=doc.title or doc.url,
                quote=quote,
                summary=_summary(content),
                score=score,
                published_at=doc.published_at,
                metadata={
                    **doc.metadata,
                    "extraction_method": doc.extraction_method,
                    "domain_family": source_profile["domain_family"],
                    "source_types": source_profile["source_types"],
                    "ranking_reasons": ranking_reasons,
                },
            )
        )

    return sorted(ranked, key=lambda item: item.score, reverse=True)
