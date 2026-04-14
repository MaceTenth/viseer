from __future__ import annotations

import json
import sys
from urllib.error import URLError

from common import build_example_parser, build_pipeline
from websearch_agents.config import PipelineConfig
from websearch_agents.output_format import format_price_result_json, format_price_result_text
from websearch_agents.price_validation import validate_price_consensus
from websearch_agents.rich_output import (
    RICH_INSTALL_MESSAGE,
    print_json_rich,
    print_price_result_rich,
    rich_available,
    should_use_rich,
)


def main() -> None:
    parser = build_example_parser(
        description="Run a price-consensus example.",
        default_question="MacBook Air M3 13-inch price",
    )
    parser.add_argument(
        "--min-sources",
        type=int,
        default=3,
        help="Minimum independent domains needed for a supported verdict.",
    )
    args = parser.parse_args()
    base_url = args.searxng_url or PipelineConfig.from_env().searxng_url
    pipeline = build_pipeline(args=args, strategy="price")

    try:
        docs, trace = pipeline.collect_documents(args.question, limit_per_query=args.limit)
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

    result = validate_price_consensus(args.question, docs, min_sources=args.min_sources)
    rich_enabled = should_use_rich(
        explicit_rich=args.rich,
        plain=args.plain,
        stdout_is_tty=sys.stdout.isatty(),
        rich_installed=rich_available(),
        json_mode=args.as_json,
    )

    if args.as_json:
        payload = format_price_result_json(
            question=args.question,
            result=result,
            trace=trace,
            min_sources=args.min_sources,
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
            print_price_result_rich(
                question=args.question,
                result=result,
                trace=trace,
                min_sources=args.min_sources,
            )
        except RuntimeError:
            parser.exit(2, f"{RICH_INSTALL_MESSAGE}\n")
        return

    print(
        format_price_result_text(
            question=args.question,
            result=result,
            trace=trace,
            min_sources=args.min_sources,
        )
    )


if __name__ == "__main__":
    main()
