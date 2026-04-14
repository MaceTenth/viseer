from __future__ import annotations

from dataclasses import asdict
from datetime import UTC, datetime

from .types import Answer, Citation, Evidence


def build_citations(evidence: list[Evidence]) -> list[Citation]:
    accessed_at = datetime.now(UTC).isoformat()
    return [
        Citation(
            title=item.title,
            url=item.url,
            quote=item.quote,
            published_at=item.published_at,
            accessed_at=accessed_at,
        )
        for item in evidence
    ]


def render_answer(question: str, evidence: list[Evidence], strategy_name: str) -> str:
    if not evidence:
        return f"No reliable evidence found for: {question}"

    top = evidence[0]
    date_hint = f" ({top.published_at})" if top.published_at else ""
    return (
        f"Collected {len(evidence)} evidence item(s) using {strategy_name}. "
        f"Top source: {top.title}{date_hint}. {_clean_sentence(top.quote)}"
    )


def answer_to_dict(answer: Answer) -> dict:
    return asdict(answer)


def _clean_sentence(text: str) -> str:
    return " ".join(text.strip().split())
