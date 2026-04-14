from __future__ import annotations

from dataclasses import asdict, dataclass, field
import re
from typing import Any
from urllib.parse import urlparse

from .types import PageDocument

_PRICE_PATTERNS = [
    re.compile(
        r"(?P<currency>\$|USD|US\$|€|EUR|£|GBP|₪|ILS|NIS)\s?(?P<amount>\d[\d,]*(?:\.\d{1,2})?)",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?P<amount>\d[\d,]*(?:\.\d{1,2})?)\s?(?P<currency>USD|US\$|EUR|GBP|ILS|NIS|€|£|₪)",
        re.IGNORECASE,
    ),
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
    "plans",
    "month",
    "monthly",
    "year",
    "annual",
    "user",
    "seat",
    "per user",
    "per month",
}
_NEGATIVE_HINTS = {
    "delivery": 5.0,
    "shipping": 5.0,
    "checkout": 4.0,
    "tax": 3.0,
    "taxes": 3.0,
    "fee": 3.0,
    "financing": 4.0,
    "installment": 4.0,
    "monthly payment": 4.0,
    "apr": 4.0,
    "trade-in": 4.0,
    "trade in": 4.0,
    "gift card": 4.0,
    "coupon": 3.0,
    "discount": 2.5,
    "save": 2.0,
    "off": 1.0,
    "renewed": 5.0,
    "refurbished": 5.0,
    "used": 4.0,
    "offers from": 3.0,
    "trial": 3.0,
}
_SECONDARY_MARKET_TERMS = {
    "renewed",
    "refurbished",
    "used",
    "pre-owned",
    "open-box",
    "open box",
}
_GENERIC_QUESTION_TERMS = {
    "a",
    "an",
    "and",
    "current",
    "for",
    "how",
    "is",
    "of",
    "on",
    "per",
    "plan",
    "plans",
    "price",
    "pricing",
    "subscription",
    "the",
    "what",
}
_QUESTION_OPTION_TERMS = {"team", "business", "enterprise", "plus", "pro", "ai", "m3", "m4", "13", "15"}
_STRICT_OPTION_TERMS = {"team", "business", "enterprise", "plus", "pro", "ai"}
_SUBSCRIPTION_TERMS = {
    "subscription",
    "plan",
    "plans",
    "pricing",
    "team",
    "business",
    "enterprise",
    "plus",
    "pro",
    "ai",
    "user",
    "seat",
}
_CURRENCY_MAP = {
    "$": "USD",
    "USD": "USD",
    "US$": "USD",
    "€": "EUR",
    "EUR": "EUR",
    "£": "GBP",
    "GBP": "GBP",
    "₪": "ILS",
    "ILS": "ILS",
    "NIS": "ILS",
}
_MIN_ACCEPTED_SCORE = 1.0


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


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def _normalize_amount(raw: str) -> float:
    return float(raw.replace(",", ""))


def _normalize_currency(raw: str) -> str:
    key = raw.upper() if raw.isalpha() else raw
    return _CURRENCY_MAP[key]


def _domain(url: str) -> str:
    return urlparse(url).netloc.lower()


def _iter_lines(text: str) -> list[str]:
    lines: list[str] = []
    for raw in text.splitlines():
        line = re.sub(r"\s+", " ", raw).strip()
        if line:
            lines.append(line)
    return lines


def _question_terms(question: str) -> set[str]:
    return set(_tokenize(question))


def _focus_terms(question: str) -> set[str]:
    tokens = {
        token
        for token in _tokenize(question)
        if token not in _GENERIC_QUESTION_TERMS and (len(token) > 2 or token.isdigit() or token in _QUESTION_OPTION_TERMS)
    }
    return tokens


def _specific_focus_terms(question: str) -> set[str]:
    tokens = set(_tokenize(question))
    return {token for token in tokens if token in _QUESTION_OPTION_TERMS or token.isdigit()}


def _build_text(doc: PageDocument) -> str:
    parts = [
        doc.title,
        str(doc.metadata.get("search_snippet", "")),
        doc.text[:12000],
    ]
    return "\n".join(part for part in parts if part).strip()


def _line_context(lines: list[str], index: int) -> str:
    start = max(0, index - 1)
    end = min(len(lines), index + 2)
    return "\n".join(lines[start:end]).strip()


def _is_clause_separator(text: str, index: int) -> bool:
    char = text[index]
    if char in {";", "|", "•", "·", "\n"}:
        return True
    prev_char = text[index - 1] if index > 0 else ""
    next_char = text[index + 1] if index + 1 < len(text) else ""
    if char in {",", "."} and not (prev_char.isdigit() and next_char.isdigit()):
        return True
    return False


def _match_window(text: str, start: int, end: int, radius: int = 24) -> str:
    left = start
    right = end
    while left > 0 and not _is_clause_separator(text, left - 1):
        left -= 1
    while right < len(text) and not _is_clause_separator(text, right):
        right += 1
    snippet = text[left:right].strip(" ,.;|•·")
    if snippet:
        return snippet
    left = max(0, start - radius)
    right = min(len(text), end + radius)
    return text[left:right].strip()


def _range_position(line: str, start: int, end: int) -> str | None:
    before = line[max(0, start - 3) : start]
    after = line[end : min(len(line), end + 3)]
    if any(token in after for token in ("-", "–", "—")):
        return "lower"
    if any(token in before for token in ("-", "–", "—")):
        return "upper"
    return None


def _candidate_score(
    *,
    question_terms: set[str],
    focus_terms: set[str],
    specific_focus_terms: set[str],
    title: str,
    url: str,
    match_window: str,
    context: str,
    amount: float,
    range_position: str | None,
) -> float:
    combined = " ".join([title, url, context]).lower()
    combined_terms = set(_tokenize(combined))
    precise_terms = set(_tokenize(" ".join([title, url, match_window])))
    strict_terms = {term for term in specific_focus_terms if term in _STRICT_OPTION_TERMS}
    loose_terms = specific_focus_terms - strict_terms
    lowered_context = context.lower()
    lowered_precise = " ".join([title, url, match_window]).lower()
    subscription_like_query = bool(question_terms & _SUBSCRIPTION_TERMS)

    if amount < 0:
        return -10.0
    if not question_terms & _SECONDARY_MARKET_TERMS and any(
        term in lowered_precise for term in _SECONDARY_MARKET_TERMS
    ):
        return -10.0

    overlap = 0.4 * len(question_terms & combined_terms)
    focus_overlap = 2.5 * len(focus_terms & combined_terms)
    pricing_hints = 0.4 * sum(1.0 for hint in _PRICING_HINTS if hint in lowered_context)
    score = overlap + focus_overlap + pricing_hints

    if focus_terms and not (focus_terms & combined_terms):
        score -= 4.0
    if strict_terms and not (strict_terms & precise_terms):
        score -= 6.0
    if loose_terms and not (loose_terms & combined_terms):
        score -= 3.0

    if amount == 0 and "free" not in question_terms:
        return -10.0
    if 0 < amount < 5 and not {"price", "pricing", "cost"} & focus_terms:
        score -= 1.0
    if not subscription_like_query and any(hint in lowered_context for hint in ("per month", "monthly payment", "month", "finance")):
        score -= 5.0

    for hint, penalty in _NEGATIVE_HINTS.items():
        if hint in lowered_context or hint in lowered_precise:
            score -= penalty

    if "msrp" in lowered_precise and "price" not in lowered_precise and "starting" not in lowered_precise:
        score -= 1.5
    if range_position == "lower":
        score -= 0.35
    elif range_position == "upper":
        score += 0.15

    if "official" in lowered_context:
        score += 1.0
    if "/pricing" in url.lower() or "/price" in url.lower():
        score += 1.0
    return score


def extract_price_evidence(question: str, docs: list[PageDocument]) -> list[PriceEvidence]:
    question_terms = _question_terms(question)
    focus_terms = _focus_terms(question)
    specific_focus_terms = _specific_focus_terms(question)
    best_by_domain: dict[str, PriceEvidence] = {}

    for doc in docs:
        source_text = _build_text(doc)
        lines = _iter_lines(source_text)
        doc_domain = _domain(doc.url)

        for index, line in enumerate(lines):
            for pattern in _PRICE_PATTERNS:
                for match in pattern.finditer(line):
                    currency = _normalize_currency(match.group("currency"))
                    amount = _normalize_amount(match.group("amount"))
                    context = _line_context(lines, index)
                    match_window = _match_window(line, match.start(), match.end())
                    score = _candidate_score(
                        question_terms=question_terms,
                        focus_terms=focus_terms,
                        specific_focus_terms=specific_focus_terms,
                        title=doc.title or doc.url,
                        url=doc.url,
                        match_window=match_window,
                        context=context,
                        amount=amount,
                        range_position=_range_position(line, match.start(), match.end()),
                    )
                    if score < _MIN_ACCEPTED_SCORE:
                        continue
                    candidate = PriceEvidence(
                        amount=amount,
                        currency=currency,
                        source_title=doc.title or doc.url,
                        source_url=doc.url,
                        domain=doc_domain,
                        snippet=match_window,
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
        elif len(group) == len(best_group) and group:
            if sum(item.score for item in group) > sum(item.score for item in best_group):
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
