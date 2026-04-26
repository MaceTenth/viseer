from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from urllib.error import URLError

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from websearch_agents.config import DEFAULT_REDDIT_URL, DEFAULT_SEARXNG_URL, PipelineConfig
from websearch_agents.fetch.reddit import RedditThreadFetcher
from websearch_agents.fetch.reddit_extractor import RedditThreadExtractor
from websearch_agents.output_format import format_answer_json, format_answer_text
from websearch_agents.pipeline import SearchPipeline
from websearch_agents.providers.reddit import REDDIT_SORTS, REDDIT_TIME_FILTERS, RedditProvider
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
    parser.add_argument("--provider", choices=("searxng", "reddit"), default=None)
    parser.add_argument("--engine")
    parser.add_argument("--strategy", default=None)
    parser.add_argument(
        "--reddit-url",
        help=f"Reddit base URL. Defaults to {DEFAULT_REDDIT_URL} or $REDDIT_BASE_URL.",
    )
    parser.add_argument("--subreddit")
    parser.add_argument("--reddit-sort", choices=sorted(REDDIT_SORTS), default=None)
    parser.add_argument("--reddit-time", choices=sorted(REDDIT_TIME_FILTERS), default=None)
    parser.add_argument("--reddit-comment-limit", type=int, default=None)
    parser.add_argument("--reddit-include-over-18", action="store_true")
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
    provider_name = (args.provider or config.search_provider).strip().lower()
    if provider_name not in {"searxng", "reddit"}:
        raise ValueError("Unknown provider. Valid options: searxng, reddit")
    selected_strategy = args.strategy or strategy
    if provider_name == "reddit":
        if args.engine:
            raise ValueError("--engine can only be used with --provider searxng")
        reddit_comment_limit = args.reddit_comment_limit or config.reddit_comment_limit
        return SearchPipeline(
            provider=RedditProvider(
                base_url=args.reddit_url or config.reddit_base_url,
                subreddit=args.subreddit or config.reddit_subreddit,
                sort=args.reddit_sort or config.reddit_sort,
                time_filter=args.reddit_time or config.reddit_time,
                include_over_18=args.reddit_include_over_18 or config.reddit_include_over_18,
                timeout=config.request_timeout,
                user_agent=config.user_agent,
                bearer_token=config.reddit_bearer_token,
            ),
            strategy=resolve_strategy(selected_strategy),
            config=config,
            fetcher=RedditThreadFetcher(
                timeout=config.request_timeout,
                user_agent=config.user_agent,
                comment_limit=reddit_comment_limit,
                bearer_token=config.reddit_bearer_token,
            ),
            extractor=RedditThreadExtractor(
                max_comments=reddit_comment_limit,
                weak_text_threshold=config.weak_text_threshold,
                max_json_fetches=config.recovery_json_limit,
            ),
        )

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
        strategy=resolve_strategy(selected_strategy),
        config=config,
    )


def run_example(*, strategy: str, default_question: str, description: str) -> None:
    parser = build_example_parser(description=description, default_question=default_question)
    args = parser.parse_args()
    config = PipelineConfig.from_env()
    provider_name = (args.provider or config.search_provider).strip().lower()
    if provider_name == "reddit":
        base_url = args.reddit_url or config.reddit_base_url
    else:
        base_url = args.searxng_url or config.searxng_url
    try:
        pipeline = build_pipeline(args=args, strategy=strategy)
    except ValueError as exc:
        parser.exit(2, f"{exc}\n")
    try:
        answer = pipeline.run(args.question, limit_per_query=args.limit)
    except URLError as exc:
        if provider_name == "reddit":
            parser.exit(
                2,
                (
                    f"Could not reach Reddit at {base_url}.\n"
                    "Set REDDIT_BEARER_TOKEN if your environment requires authenticated Reddit API access.\n"
                    f"Original error: {exc}\n"
                ),
            )
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
