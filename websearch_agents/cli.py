from __future__ import annotations

import argparse
import json
import sys
from urllib.error import URLError

from .config import DEFAULT_SEARXNG_URL, PipelineConfig
from .output_format import format_answer_json, format_answer_text
from .pipeline import SearchPipeline
from .providers.searxng import SearxngProvider
from .rich_output import (
    RICH_INSTALL_MESSAGE,
    print_answer_rich,
    print_json_rich,
    rich_available,
    should_use_rich,
)
from .strategies import resolve_strategy


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Viseer: grounded search and validation for AI agents.")
    parser.add_argument("question")
    parser.add_argument(
        "--searxng-url",
        help=f"SearXNG base URL. Defaults to {DEFAULT_SEARXNG_URL} or $SEARXNG_URL.",
    )
    parser.add_argument("--engine")
    parser.add_argument("--strategy", default="direct")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--json", action="store_true", dest="as_json")
    style_group = parser.add_mutually_exclusive_group()
    style_group.add_argument(
        "--rich",
        action="store_true",
        help="Force Rich output. Requires `pip install -e .[ui]`.",
    )
    style_group.add_argument(
        "--plain",
        action="store_true",
        help="Disable Rich output even when it is available.",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    config = PipelineConfig.from_env()
    base_url = args.searxng_url or config.searxng_url
    if args.engine:
        config.engine = args.engine

    provider = SearxngProvider(
        base_url=base_url,
        engine=config.engine,
        timeout=config.request_timeout,
        user_agent=config.user_agent,
    )
    pipeline = SearchPipeline(provider=provider, strategy=resolve_strategy(args.strategy), config=config)
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

    payload = format_answer_json(answer)
    rich_enabled = should_use_rich(
        explicit_rich=args.rich,
        plain=args.plain,
        stdout_is_tty=sys.stdout.isatty(),
        rich_installed=rich_available(),
        json_mode=args.as_json,
    )
    if args.as_json:
        if args.rich and not rich_enabled:
            parser.exit(2, f"{RICH_INSTALL_MESSAGE}\n")
        if rich_enabled:
            try:
                print_json_rich(payload)
            except RuntimeError:
                parser.exit(2, f"{RICH_INSTALL_MESSAGE}\n")
        else:
            print(json.dumps(payload, indent=2, ensure_ascii=False))
            return

    if args.rich and not rich_enabled:
        parser.exit(2, f"{RICH_INSTALL_MESSAGE}\n")

    if rich_enabled:
        try:
            print_answer_rich(answer)
        except RuntimeError:
            parser.exit(2, f"{RICH_INSTALL_MESSAGE}\n")
        return

    print(format_answer_text(answer))


if __name__ == "__main__":
    main()
