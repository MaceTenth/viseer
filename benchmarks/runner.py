from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
import statistics
import time
from typing import Any
from urllib.error import URLError

from websearch_agents.config import PipelineConfig
from websearch_agents.output_format import (
    format_answer_json,
    format_page_document_json,
    format_price_result_json,
)
from websearch_agents.page_fetch import fetch_page_document
from websearch_agents.pipeline import SearchPipeline
from websearch_agents.price_validation import validate_price_consensus
from websearch_agents.providers.searxng import SearxngProvider
from websearch_agents.strategies import resolve_strategy

SCHEMA_VERSION = "1.0"


@dataclass(slots=True)
class BenchmarkTask:
    id: str
    kind: str
    category: str
    strategy: str | None = None
    question: str | None = None
    url: str | None = None
    must_include_all: list[str] = field(default_factory=list)
    must_include_any: list[str] = field(default_factory=list)
    expected_source_hints: list[str] = field(default_factory=list)
    expected_verdict: str | None = None
    min_evidence: int = 0
    min_chars: int = 0
    min_sources: int = 3
    notes: str = ""

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "BenchmarkTask":
        return cls(
            id=str(payload["id"]),
            kind=str(payload["kind"]),
            category=str(payload["category"]),
            strategy=payload.get("strategy"),
            question=payload.get("question"),
            url=payload.get("url"),
            must_include_all=[str(item) for item in payload.get("must_include_all", [])],
            must_include_any=[str(item) for item in payload.get("must_include_any", [])],
            expected_source_hints=[str(item) for item in payload.get("expected_source_hints", [])],
            expected_verdict=payload.get("expected_verdict"),
            min_evidence=int(payload.get("min_evidence", 0)),
            min_chars=int(payload.get("min_chars", 0)),
            min_sources=int(payload.get("min_sources", 3)),
            notes=str(payload.get("notes", "")),
        )


def load_tasks(path: Path) -> list[BenchmarkTask]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return [BenchmarkTask.from_dict(item) for item in payload]


def _normalize(value: str) -> str:
    return " ".join(value.lower().split())


def _contains_phrase(blob: str, phrase: str) -> bool:
    return _normalize(phrase) in _normalize(blob)


def _answer_blob(payload: dict[str, Any]) -> tuple[str, list[str], int]:
    sources = payload.get("sources", [])
    parts = [str(payload.get("result", {}).get("summary", ""))]
    for item in sources:
        parts.extend(
            [
                str(item.get("title", "")),
                str(item.get("quote", "")),
                str(item.get("summary", "")),
                str(item.get("url", "")),
            ]
        )
    return "\n".join(parts), [str(item.get("url", "")) for item in sources], len(sources)


def _price_blob(payload: dict[str, Any]) -> tuple[str, list[str], int]:
    agreeing = payload.get("agreeing_sources", [])
    conflicting = payload.get("conflicting_sources", [])
    sources = agreeing + conflicting
    parts = [
        str(payload.get("result", {}).get("summary", "")),
        str(payload.get("result", {}).get("verdict", "")),
    ]
    for item in sources:
        parts.extend(
            [
                str(item.get("title", "")),
                str(item.get("snippet", "")),
                str(item.get("url", "")),
                str(item.get("price", {}).get("amount", "")),
                str(item.get("price", {}).get("currency", "")),
            ]
        )
    return "\n".join(parts), [str(item.get("url", "")) for item in sources], len(sources)


def _fetch_blob(payload: dict[str, Any]) -> tuple[str, list[str], int, int]:
    result = payload.get("result", {})
    blob = "\n".join(
        [
            str(result.get("title", "")),
            str(result.get("url", "")),
            str(result.get("text", "")),
        ]
    )
    char_count = int(result.get("char_count", 0))
    return blob, [str(result.get("url", ""))], 1, char_count


def evaluate_task_checks(task: BenchmarkTask, payload: dict[str, Any]) -> dict[str, Any]:
    if task.kind == "answer":
        blob, source_urls, evidence_count = _answer_blob(payload)
        verdict = None
        char_count = None
    elif task.kind == "price":
        blob, source_urls, evidence_count = _price_blob(payload)
        verdict = str(payload.get("result", {}).get("verdict", ""))
        char_count = None
    else:
        blob, source_urls, evidence_count, char_count = _fetch_blob(payload)
        verdict = None

    checks: dict[str, Any] = {}
    if task.must_include_all:
        checks["must_include_all"] = all(_contains_phrase(blob, item) for item in task.must_include_all)
    if task.must_include_any:
        checks["must_include_any"] = any(_contains_phrase(blob, item) for item in task.must_include_any)
    if task.expected_source_hints:
        hint_hits = sum(
            1
            for hint in task.expected_source_hints
            if any(hint.lower() in url.lower() for url in source_urls)
        )
        checks["source_hint_hits"] = hint_hits
        checks["source_hints_present"] = hint_hits > 0
    if task.expected_verdict:
        checks["expected_verdict"] = verdict == task.expected_verdict
    if task.min_evidence:
        checks["min_evidence"] = evidence_count >= task.min_evidence
    if task.min_chars:
        checks["min_chars"] = bool(char_count is not None and char_count >= task.min_chars)

    bool_checks = [value for value in checks.values() if isinstance(value, bool)]
    passed = sum(1 for value in bool_checks if value)
    total = len(bool_checks)
    automatic_score = round(passed / total, 2) if total else 1.0
    if automatic_score >= 1.0:
        status = "pass"
    elif automatic_score >= 0.5:
        status = "mixed"
    else:
        status = "fail"

    checks["automatic_score"] = automatic_score
    checks["automatic_status"] = status
    checks["evidence_count"] = evidence_count
    if verdict is not None:
        checks["observed_verdict"] = verdict
    if char_count is not None:
        checks["observed_char_count"] = char_count
    return checks


def summarize_results(results: list[dict[str, Any]]) -> dict[str, Any]:
    if not results:
        return {
            "task_count": 0,
            "pass_count": 0,
            "mixed_count": 0,
            "fail_count": 0,
            "median_latency_ms": 0,
            "average_automatic_score": 0.0,
            "by_category": {},
        }

    latencies = [int(item["latency_ms"]) for item in results]
    by_category: dict[str, dict[str, Any]] = {}
    pass_count = mixed_count = fail_count = 0
    for item in results:
        status = item["checks"]["automatic_status"]
        if status == "pass":
            pass_count += 1
        elif status == "mixed":
            mixed_count += 1
        else:
            fail_count += 1

        bucket = by_category.setdefault(
            item["category"],
            {"task_count": 0, "pass_count": 0, "mixed_count": 0, "fail_count": 0},
        )
        bucket["task_count"] += 1
        bucket[f"{status}_count"] += 1

    return {
        "task_count": len(results),
        "pass_count": pass_count,
        "mixed_count": mixed_count,
        "fail_count": fail_count,
        "median_latency_ms": int(statistics.median(latencies)),
        "average_automatic_score": round(
            sum(float(item["checks"]["automatic_score"]) for item in results) / len(results),
            2,
        ),
        "by_category": by_category,
    }


def build_markdown_report(run_payload: dict[str, Any]) -> str:
    run = run_payload["run"]
    summary = run_payload["summary"]
    lines = [
        f"# Viseer Benchmark Results ({run['started_at'][:10]})",
        "",
        "This is the first lightweight benchmark pass for Viseer.",
        "It uses automatic checks over a small set of real-world tasks and should be read as a trust and behavior snapshot, not a leaderboard claim.",
        "",
        "## Run Summary",
        "",
        f"- Tasks: {summary['task_count']}",
        f"- Pass: {summary['pass_count']}",
        f"- Mixed: {summary['mixed_count']}",
        f"- Fail: {summary['fail_count']}",
        f"- Average automatic score: {summary['average_automatic_score']:.2f}",
        f"- Median latency: {summary['median_latency_ms']} ms",
        f"- SearXNG URL: {run['searxng_url']}",
        "",
        "## By Category",
        "",
        "| Category | Tasks | Pass | Mixed | Fail |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for category, bucket in sorted(summary["by_category"].items()):
        lines.append(
            f"| {category} | {bucket['task_count']} | {bucket['pass_count']} | {bucket['mixed_count']} | {bucket['fail_count']} |"
        )

    lines.extend(
        [
            "",
            "## Task Table",
            "",
            "| Task | Kind | Category | Status | Score | Latency | Notes |",
            "| --- | --- | --- | --- | ---: | ---: | --- |",
        ]
    )
    for item in run_payload["tasks"]:
        lines.append(
            "| "
            f"{item['id']} | {item['kind']} | {item['category']} | {item['checks']['automatic_status']} | "
            f"{item['checks']['automatic_score']:.2f} | {item['latency_ms']} ms | {item.get('notes', '')} |"
        )

    lines.extend(["", "## Detailed Results", ""])
    for item in run_payload["tasks"]:
        lines.extend(
            [
                f"### {item['id']}",
                "",
                f"- Kind: {item['kind']}",
                f"- Category: {item['category']}",
                f"- Status: {item['checks']['automatic_status']}",
                f"- Automatic score: {item['checks']['automatic_score']:.2f}",
                f"- Latency: {item['latency_ms']} ms",
                f"- Prompt: {item.get('question') or item.get('url')}",
                f"- Summary: {item['observed_summary']}",
                f"- Top sources: {', '.join(item['top_source_urls'][:3]) or '-'}",
            ]
        )
        if item.get("notes"):
            lines.append(f"- Notes: {item['notes']}")
        lines.append("- Checks:")
        for key, value in item["checks"].items():
            if key in {"automatic_score", "automatic_status"}:
                continue
            lines.append(f"  - {key}: {value}")
        lines.append("")

    return "\n".join(lines).strip() + "\n"


def _pipeline_for_task(task: BenchmarkTask, config: PipelineConfig, searxng_url: str) -> SearchPipeline:
    return SearchPipeline(
        provider=SearxngProvider(
            base_url=searxng_url,
            engine=config.engine,
            timeout=config.request_timeout,
            user_agent=config.user_agent,
        ),
        strategy=resolve_strategy(task.strategy),
        config=config,
    )


def run_task(task: BenchmarkTask, *, config: PipelineConfig, searxng_url: str) -> dict[str, Any]:
    started = time.perf_counter()
    if task.kind == "answer":
        pipeline = _pipeline_for_task(task, config, searxng_url)
        answer = pipeline.run(task.question or "")
        payload = format_answer_json(answer)
        observed_summary = str(payload["result"]["summary"])
        top_source_urls = [str(item.get("url", "")) for item in payload.get("sources", [])]
    elif task.kind == "price":
        pipeline = _pipeline_for_task(task, config, searxng_url)
        docs, trace = pipeline.collect_documents(task.question or "")
        price_result = validate_price_consensus(task.question or "", docs, min_sources=task.min_sources)
        payload = format_price_result_json(
            question=task.question or "",
            result=price_result,
            trace=trace,
            min_sources=task.min_sources,
        )
        observed_summary = str(payload["result"]["summary"])
        top_source_urls = [
            str(item.get("url", ""))
            for item in payload.get("agreeing_sources", []) + payload.get("conflicting_sources", [])
        ]
    elif task.kind == "fetch":
        document = fetch_page_document(task.url or "", config=config)
        payload = format_page_document_json(document)
        observed_summary = str(payload["result"]["title"])
        top_source_urls = [str(payload["result"]["url"])]
    else:
        raise ValueError(f"Unsupported benchmark task kind: {task.kind}")

    latency_ms = int((time.perf_counter() - started) * 1000)
    checks = evaluate_task_checks(task, payload)
    return {
        "id": task.id,
        "kind": task.kind,
        "category": task.category,
        "strategy": task.strategy,
        "question": task.question,
        "url": task.url,
        "latency_ms": latency_ms,
        "notes": task.notes,
        "observed_summary": observed_summary,
        "top_source_urls": top_source_urls,
        "checks": checks,
        "payload": payload,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the small Viseer benchmark set.")
    parser.add_argument("--tasks", default="benchmarks/tasks.json", help="Path to the task JSON file.")
    parser.add_argument("--output", required=True, help="Path to write the benchmark JSON results.")
    parser.add_argument("--markdown", help="Optional path to write a Markdown report.")
    parser.add_argument(
        "--searxng-url",
        help="Override the SearXNG base URL. Defaults to $SEARXNG_URL or the local Docker instance.",
    )
    parser.add_argument("--task", action="append", dest="task_ids", help="Run only the given task id. Repeatable.")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    config = PipelineConfig.from_env()
    searxng_url = args.searxng_url or config.searxng_url
    tasks = load_tasks(Path(args.tasks))
    if args.task_ids:
        allowed = {item.strip() for item in args.task_ids}
        tasks = [task for task in tasks if task.id in allowed]
    if not tasks:
        parser.exit(2, "No benchmark tasks selected.\n")

    started_at = datetime.now(UTC).isoformat()
    results: list[dict[str, Any]] = []
    try:
        for task in tasks:
            results.append(run_task(task, config=config, searxng_url=searxng_url))
    except URLError as exc:
        parser.exit(
            2,
            (
                f"Could not reach SearXNG at {searxng_url}.\n"
                "Start the bundled local instance with `docker compose up -d`, "
                "or pass a different URL with `--searxng-url`.\n"
                f"Original error: {exc}\n"
            ),
        )

    finished_at = datetime.now(UTC).isoformat()
    summary = summarize_results(results)
    run_payload = {
        "schema_version": SCHEMA_VERSION,
        "run": {
            "started_at": started_at,
            "finished_at": finished_at,
            "task_count": len(results),
            "searxng_url": searxng_url,
        },
        "summary": summary,
        "tasks": results,
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(run_payload, indent=2, ensure_ascii=False), encoding="utf-8")

    if args.markdown:
        markdown_path = Path(args.markdown)
        markdown_path.parent.mkdir(parents=True, exist_ok=True)
        markdown_path.write_text(build_markdown_report(run_payload), encoding="utf-8")


if __name__ == "__main__":
    main()
