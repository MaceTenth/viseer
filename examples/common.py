from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from urllib.error import URLError

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from websearch_agents.config import DEFAULT_SEARXNG_URL, PipelineConfig
from websearch_agents.output_format import format_answer_json, format_answer_text
from websearch_agents.pipeline import SearchPipeline
from websearch_agents.providers.searxng import SearxngProvider
from websearch_agents.rich_output import (
    RICH_INSTALL_MESSAGE,
    print_answer_rich,
    print_json_rich,
    rich_available,
    should_use_rich,
)
from websearch_agents.strategies import resolve_strategy


def build_example_parser(description: str, default_question: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("question", nargs="?", default=default_question)
    parser.add_argument(
        "--searxng-url",
        help=f"SearXNG base URL. Defaults to {DEFAULT_SEARXNG_URL} or $SEARXNG_URL.",
    )
    parser.add_argument("--engine")
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


def build_pipeline(*, args, strategy: str) -> SearchPipeline:
    config = PipelineConfig.from_env()
    if args.engine:
        config.engine = args.engine

    base_url = args.searxng_url or config.searxng_url

    return SearchPipeline(
        provider=SearxngProvider(
            base_url=base_url,
            engine=config.engine,
            timeout=config.request_timeout,
            user_agent=config.user_agent,
        ),
        strategy=resolve_strategy(strategy),
        config=config,
    )


def run_example(*, strategy: str, default_question: str, description: str) -> None:
    parser = build_example_parser(description=description, default_question=default_question)
    args = parser.parse_args()
    base_url = args.searxng_url or PipelineConfig.from_env().searxng_url
    pipeline = build_pipeline(args=args, strategy=strategy)
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
