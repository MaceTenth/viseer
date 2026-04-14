from __future__ import annotations

from dataclasses import asdict, dataclass, field
import re
from typing import Any
from urllib.parse import urlparse

from .types import PageDocument

_PRICE_PATTERNS = [
    re.compile(r"(?P<currency>\$|USD)\s?(?P<amount>\d[\d,]*(?:\.\d{2})?)", re.IGNORECASE),
    re.compile(r"(?P<currency>€|EUR)\s?(?P<amount>\d[\d,]*(?:\.\d{2})?)", re.IGNORECASE),
    re.compile(r"(?P<currency>£|GBP)\s?(?P<amount>\d[\d,]*(?:\.\d{2})?)", re.IGNORECASE),
]
_PRICING_HINTS = {
    "price",
    "pricing",
    "buy",
    "sale",
    "from",
    "starting",
    "starts",
    "msrp",
    "plan",
    "month",
    "year",
}
_CURRENCY_MAP = {
    "$": "USD",
    "USD": "USD",
    "€": "EUR",
    "EUR": "EUR",
    "£": "GBP",
    "GBP": "GBP",
}


@dataclass(slots=True)
class PriceEvidence:
    amount: float
    currency: str
    source_title: str
    source_url: str
    domain: str
    snippet: str
    score: float
    published_at: str | None = None


@dataclass(slots=True)
class PriceConsensusResult:
    question: str
    verdict: str
    summary: str
    confidence: float
    consensus_amount: float | None
    consensus_currency: str | None
    agreeing: list[PriceEvidence] = field(default_factory=list)
    conflicting: list[PriceEvidence] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


def _normalize_amount(raw: str) -> float:
    return float(raw.replace(",", ""))


def _domain(url: str) -> str:
    return urlparse(url).netloc.lower()


def _context_window(text: str, start: int, end: int, window: int = 60) -> str:
    return text[max(0, start - window) : min(len(text), end + window)].strip()


def _candidate_score(question_terms: set[str], context: str, amount: float) -> float:
    context_terms = set(re.findall(r"[a-z0-9]+", context.lower()))
    overlap = float(len(question_terms & context_terms))
    pricing_hints = sum(1.0 for hint in _PRICING_HINTS if hint in context.lower())
    if amount <= 0:
        return -1.0
    return overlap + pricing_hints


def extract_price_evidence(question: str, docs: list[PageDocument]) -> list[PriceEvidence]:
    question_terms = set(re.findall(r"[a-z0-9]+", question.lower()))
    best_by_domain: dict[str, PriceEvidence] = {}

    for doc in docs:
        text = doc.text[:6000]
        doc_domain = _domain(doc.url)
        for pattern in _PRICE_PATTERNS:
            for match in pattern.finditer(text):
                raw_currency = match.group("currency")
                key = raw_currency.upper() if raw_currency.isalpha() else raw_currency
                currency = _CURRENCY_MAP[key]
                amount = _normalize_amount(match.group("amount"))
                context = _context_window(text, match.start(), match.end())
                score = _candidate_score(question_terms, context, amount)
                candidate = PriceEvidence(
                    amount=amount,
                    currency=currency,
                    source_title=doc.title or doc.url,
                    source_url=doc.url,
                    domain=doc_domain,
                    snippet=context,
                    score=score,
                    published_at=doc.published_at,
                )
                previous = best_by_domain.get(doc_domain)
                if previous is None or candidate.score > previous.score:
                    best_by_domain[doc_domain] = candidate

    return sorted(best_by_domain.values(), key=lambda item: item.score, reverse=True)


def _same_bucket(left: PriceEvidence, right: PriceEvidence) -> bool:
    if left.currency != right.currency:
        return False
    if left.amount == right.amount:
        return True
    tolerance = max(1.0, left.amount * 0.03)
    return abs(left.amount - right.amount) <= tolerance


def validate_price_consensus(
    question: str,
    docs: list[PageDocument],
    min_sources: int = 3,
) -> PriceConsensusResult:
    prices = extract_price_evidence(question, docs)
    if not prices:
        return PriceConsensusResult(
            question=question,
            verdict="insufficient",
            summary="No price evidence could be extracted from the fetched pages.",
            confidence=0.0,
            consensus_amount=None,
            consensus_currency=None,
            metadata={"sources_considered": len(docs), "price_mentions": 0},
        )

    best_group: list[PriceEvidence] = []
    for candidate in prices:
        group = [item for item in prices if _same_bucket(candidate, item)]
        if len(group) > len(best_group):
            best_group = group

    agreeing_domains = {item.domain for item in best_group}
    agreeing = sorted(best_group, key=lambda item: (-item.score, item.source_url))
    conflicting = [item for item in prices if item not in best_group]

    if len(agreeing_domains) >= min_sources:
        verdict = "supported"
    elif len(prices) >= 2 and conflicting:
        verdict = "mixed"
    else:
        verdict = "insufficient"

    consensus_amount = agreeing[0].amount if agreeing else None
    consensus_currency = agreeing[0].currency if agreeing else None
    confidence = min(1.0, len(agreeing_domains) / max(min_sources, 1))
    if verdict == "mixed":
        confidence *= 0.6
    elif verdict == "insufficient":
        confidence *= 0.3

    if consensus_amount is None:
        summary = "Price evidence was found, but no stable consensus emerged."
    else:
        summary = (
            f"Consensus price: {consensus_currency} {consensus_amount:,.2f} "
            f"based on {len(agreeing_domains)} independent source(s)."
        )
        if conflicting:
            summary += f" {len(conflicting)} source(s) disagreed or showed another price."

    return PriceConsensusResult(
        question=question,
        verdict=verdict,
        summary=summary,
        confidence=round(confidence, 2),
        consensus_amount=consensus_amount,
        consensus_currency=consensus_currency,
        agreeing=agreeing,
        conflicting=conflicting,
        metadata={"sources_considered": len(docs), "price_mentions": len(prices)},
    )


def price_consensus_to_dict(result: PriceConsensusResult) -> dict[str, Any]:
    return asdict(result)
