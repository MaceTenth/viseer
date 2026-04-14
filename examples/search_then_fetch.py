from __future__ import annotations

import json
import sys
from urllib.error import URLError

from common import build_example_parser, build_pipeline
from websearch_agents.config import PipelineConfig
from websearch_agents.output_format import (
    format_answer_json,
    format_answer_text,
    format_page_document_json,
    format_page_document_text,
)
from websearch_agents.page_fetch import fetch_page_document
from websearch_agents.rich_output import (
    RICH_INSTALL_MESSAGE,
    print_answer_rich,
    print_json_rich,
    print_page_document_rich,
    rich_available,
    should_use_rich,
)

STRATEGY_CHOICES = ("direct", "latest", "verify", "compare", "price")


def _combined_payload(*, question: str, strategy: str, source_rank: int, max_chars: int, answer, document) -> dict:
    selected = answer.evidence[source_rank - 1]
    return {
        "schema_version": "1.0",
        "kind": "search_then_fetch",
        "request": {
            "question": question,
            "strategy": strategy,
            "source_rank": source_rank,
            "max_chars": max_chars,
        },
        "selected_source": {
            "rank": source_rank,
            "title": selected.title,
            "url": selected.url,
            "score": round(selected.score, 2),
        },
        "search": format_answer_json(answer),
        "page": format_page_document_json(document, max_chars=max_chars),
    }


def _combined_text(*, source_rank: int, answer, document, max_chars: int) -> str:
    selected = answer.evidence[source_rank - 1]
    selected_source = "\n".join(
        [
            "SELECTED SOURCE",
            f"[{source_rank}] {selected.title}",
            f"URL: {selected.url}",
            f"Score: {selected.score:.2f}",
        ]
    )
    return "\n\n".join(
        [
            format_answer_text(answer),
            selected_source,
            format_page_document_text(document, max_chars=max_chars),
        ]
    )


def main() -> None:
    parser = build_example_parser(
        description="Search first, then fetch one chosen source as clean text or JSON.",
        default_question="Who founded Stripe?",
    )
    parser.add_argument(
        "--strategy",
        default="direct",
        choices=STRATEGY_CHOICES,
        help="Search strategy to use before fetching the selected source.",
    )
    parser.add_argument(
        "--source-rank",
        type=int,
        default=1,
        help="1-based source rank to fetch after search.",
    )
    parser.add_argument(
        "--max-chars",
        type=int,
        default=1500,
        help="Maximum extracted page text characters to include in the fetch step.",
    )
    args = parser.parse_args()

    base_url = args.searxng_url or PipelineConfig.from_env().searxng_url
    pipeline = build_pipeline(args=args, strategy=args.strategy)

    try:
        answer = pipeline.run(args.question, limit_per_query=args.limit)
    except URLError as exc:
        parser.exit(
            2,
            (
                f"Could not reach SearXNG at {base_url}.\n"
                "Start the bundled local instance with `docker compose up -d`, "
                "or pass a different URL with `--searxng-url`.\n"
                f"Original error: {exc}\n"
            ),
        )

    if not answer.evidence:
        parser.exit(2, "No sources were found to fetch. Try a different question or strategy.\n")

    if args.source_rank < 1 or args.source_rank > len(answer.evidence):
        parser.exit(
            2,
            (
                f"Source rank {args.source_rank} is out of range.\n"
                f"Available sources: 1-{len(answer.evidence)}.\n"
            ),
        )

    selected = answer.evidence[args.source_rank - 1]
    try:
        document = fetch_page_document(selected.url, config=pipeline.config)
    except URLError as exc:
        parser.exit(2, f"Could not fetch {selected.url}.\nOriginal error: {exc}\n")
    except ValueError as exc:
        parser.exit(2, f"{exc}\n")

    rich_enabled = should_use_rich(
        explicit_rich=args.rich,
        plain=args.plain,
        stdout_is_tty=sys.stdout.isatty(),
        rich_installed=rich_available(),
        json_mode=args.as_json,
    )

    if args.as_json:
        payload = _combined_payload(
            question=args.question,
            strategy=args.strategy,
            source_rank=args.source_rank,
            max_chars=args.max_chars,
            answer=answer,
            document=document,
        )
        if args.rich and not rich_enabled:
            parser.exit(2, f"{RICH_INSTALL_MESSAGE}\n")
        if rich_enabled:
            try:
                print_json_rich(payload)
            except RuntimeError:
                parser.exit(2, f"{RICH_INSTALL_MESSAGE}\n")
        else:
            print(json.dumps(payload, indent=2))
        return

    if args.rich and not rich_enabled:
        parser.exit(2, f"{RICH_INSTALL_MESSAGE}\n")

    if rich_enabled:
        try:
            print_answer_rich(answer)
            print(
                "\n".join(
                    [
                        "",
                        f"Selected source [{args.source_rank}]: {selected.title}",
                        selected.url,
                        "",
                    ]
                )
            )
            print_page_document_rich(document, max_chars=args.max_chars)
        except RuntimeError:
            parser.exit(2, f"{RICH_INSTALL_MESSAGE}\n")
        return

    print(
        _combined_text(
            source_rank=args.source_rank,
            answer=answer,
            document=document,
            max_chars=args.max_chars,
        )
    )


if __name__ == "__main__":
    main()
