from __future__ import annotations

from .price_validation import PriceConsensusResult
from .types import Answer, AnswerTrace, Citation, Evidence, PageDocument, QueryTrace

SCHEMA_VERSION = "1.0"


def _section(title: str, lines: list[str]) -> str:
    body = "\n".join(lines) if lines else "-"
    return f"{title}\n{body}"


def _clean_text(value: str | None) -> str:
    return (value or "").strip()


def _truncate(value: str | None, length: int = 220) -> str:
    text = _clean_text(value)
    if len(text) <= length:
        return text
    return text[: length - 3].rstrip() + "..."


def _strategy_label(name: str) -> str:
    return name.replace("_", " ").title()


def _trace_summary(trace: AnswerTrace | None) -> list[str]:
    if trace is None:
        return ["Queries: 0", "Pages fetched: 0", "Pages extracted: 0", "Failures: 0"]
    return [
        f"Queries: {len(trace.queries)}",
        f"Pages fetched: {trace.pages_fetched}",
        f"Pages extracted: {trace.pages_extracted}",
        f"Failures: {len(trace.failures)}",
    ]


def _document_counts(doc: PageDocument) -> tuple[int, int]:
    text = _clean_text(doc.text)
    return len(text.split()), len(text)


def _limit_text(text: str, max_chars: int | None) -> tuple[str, bool]:
    clean = _clean_text(text)
    if max_chars is None or max_chars <= 0 or len(clean) <= max_chars:
        return clean, False
    return clean[:max_chars].rstrip() + "...", True


def _query_trace_to_dict(trace: QueryTrace) -> dict:
    return {
        "query": trace.query,
        "result_count": trace.result_count,
        "urls": trace.urls,
    }


def _trace_to_dict(trace: AnswerTrace | None) -> dict:
    if trace is None:
        return {
            "summary": {
                "query_count": 0,
                "pages_fetched": 0,
                "pages_extracted": 0,
                "failure_count": 0,
            },
            "queries": [],
            "failures": [],
        }
    return {
        "summary": {
            "query_count": len(trace.queries),
            "pages_fetched": trace.pages_fetched,
            "pages_extracted": trace.pages_extracted,
            "failure_count": len(trace.failures),
        },
        "queries": [_query_trace_to_dict(item) for item in trace.queries],
        "failures": trace.failures,
    }


def _source_item(rank: int, evidence: Evidence, citation: Citation | None = None) -> dict:
    payload = {
        "rank": rank,
        "title": evidence.title,
        "url": evidence.url,
        "quote": evidence.quote,
        "summary": evidence.summary,
        "score": round(evidence.score, 2),
        "published_at": evidence.published_at,
        "metadata": evidence.metadata,
    }
    if citation is not None:
        payload["accessed_at"] = citation.accessed_at
    return payload


def format_answer_text(answer: Answer) -> str:
    sections = [
        _section("QUESTION", [answer.question]),
        _section("STRATEGY", [_strategy_label(answer.strategy)]),
        _section("SUMMARY", [_clean_text(answer.answer) or "No answer summary available."]),
    ]

    if answer.evidence:
        sources: list[str] = []
        for rank, item in enumerate(answer.evidence[:5], start=1):
            sources.extend(
                [
                    f"[{rank}] {item.title}",
                    f"    URL: {item.url}",
                    f"    Score: {item.score:.2f}",
                    f"    Quote: {_truncate(item.quote)}",
                ]
            )
            if item.published_at:
                sources.append(f"    Published: {item.published_at}")
        sections.append(_section("TOP SOURCES", sources))
    else:
        sections.append(_section("TOP SOURCES", ["No evidence found."]))

    sections.append(_section("TRACE", _trace_summary(answer.trace)))
    return "\n\n".join(sections)


def format_answer_json(answer: Answer) -> dict:
    citations_by_url = {item.url: item for item in answer.citations}
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": "answer",
        "request": {
            "question": answer.question,
            "strategy": answer.strategy,
        },
        "result": {
            "summary": answer.answer,
            "strategy_label": _strategy_label(answer.strategy),
            "evidence_count": len(answer.evidence),
            "documents_considered": answer.metadata.get("documents_considered", 0),
        },
        "sources": [
            _source_item(rank, item, citations_by_url.get(item.url))
            for rank, item in enumerate(answer.evidence, start=1)
        ],
        "trace": _trace_to_dict(answer.trace),
        "metadata": answer.metadata,
    }


def format_page_document_text(doc: PageDocument, max_chars: int | None = 4000) -> str:
    word_count, char_count = _document_counts(doc)
    text, truncated = _limit_text(doc.text, max_chars)
    details = [
        doc.title or "(untitled)",
        f"URL: {doc.url}",
        f"Extraction: {doc.extraction_method}",
        f"Fetched: {doc.fetched_at}",
        f"Words: {word_count}",
        f"Characters: {char_count}",
    ]
    if doc.published_at:
        details.append(f"Published: {doc.published_at}")
    if truncated:
        details.append(f"Text truncated to {max_chars} characters")

    return "\n\n".join(
        [
            _section("PAGE", details),
            _section("TEXT", [text or "No text extracted."]),
        ]
    )


def format_page_document_json(doc: PageDocument, max_chars: int | None = None) -> dict:
    word_count, char_count = _document_counts(doc)
    text, truncated = _limit_text(doc.text, max_chars)
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": "page_document",
        "request": {
            "url": doc.url,
            "max_chars": max_chars,
        },
        "result": {
            "title": doc.title,
            "url": doc.url,
            "published_at": doc.published_at,
            "fetched_at": doc.fetched_at,
            "extraction_method": doc.extraction_method,
            "word_count": word_count,
            "char_count": char_count,
            "text": text,
            "text_truncated": truncated,
        },
        "metadata": doc.metadata,
    }


def _price_source_item(rank: int, item) -> dict:
    return {
        "rank": rank,
        "title": item.source_title,
        "url": item.source_url,
        "domain": item.domain,
        "price": {
            "amount": item.amount,
            "currency": item.currency,
        },
        "snippet": item.snippet,
        "score": round(item.score, 2),
        "published_at": item.published_at,
    }


def format_price_result_text(
    question: str,
    result: PriceConsensusResult,
    trace: AnswerTrace | None = None,
    min_sources: int = 3,
) -> str:
    sections = [
        _section("QUESTION", [question]),
        _section("VERDICT", [f"{result.verdict} (confidence={result.confidence:.2f})"]),
        _section("SUMMARY", [result.summary]),
        _section("RULE", [f"Supported requires at least {min_sources} independent source(s)."]),
    ]

    if result.agreeing:
        agreeing_lines: list[str] = []
        for rank, item in enumerate(result.agreeing, start=1):
            agreeing_lines.extend(
                [
                    f"[{rank}] {item.source_title}",
                    f"    Price: {item.currency} {item.amount:,.2f}",
                    f"    URL: {item.source_url}",
                    f"    Snippet: {_truncate(item.snippet)}",
                ]
            )
        sections.append(_section("AGREEING SOURCES", agreeing_lines))

    if result.conflicting:
        conflicting_lines: list[str] = []
        for rank, item in enumerate(result.conflicting, start=1):
            conflicting_lines.extend(
                [
                    f"[{rank}] {item.source_title}",
                    f"    Price: {item.currency} {item.amount:,.2f}",
                    f"    URL: {item.source_url}",
                    f"    Snippet: {_truncate(item.snippet)}",
                ]
            )
        sections.append(_section("CONFLICTING SOURCES", conflicting_lines))

    sections.append(_section("TRACE", _trace_summary(trace)))
    return "\n\n".join(sections)


def format_price_result_json(
    question: str,
    result: PriceConsensusResult,
    trace: AnswerTrace | None = None,
    min_sources: int = 3,
) -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": "price_consensus",
        "request": {
            "question": question,
            "min_sources": min_sources,
        },
        "result": {
            "verdict": result.verdict,
            "summary": result.summary,
            "confidence": result.confidence,
            "consensus": {
                "amount": result.consensus_amount,
                "currency": result.consensus_currency,
            },
            "agreeing_source_count": len(result.agreeing),
            "conflicting_source_count": len(result.conflicting),
        },
        "agreeing_sources": [
            _price_source_item(rank, item) for rank, item in enumerate(result.agreeing, start=1)
        ],
        "conflicting_sources": [
            _price_source_item(rank, item) for rank, item in enumerate(result.conflicting, start=1)
        ],
        "trace": _trace_to_dict(trace),
        "metadata": result.metadata,
    }
