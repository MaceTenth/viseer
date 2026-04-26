from __future__ import annotations

import argparse
import json
import sys
from urllib.error import URLError

from .config import DEFAULT_REDDIT_URL, DEFAULT_SEARXNG_URL, PipelineConfig
from .fetch.reddit import RedditThreadFetcher
from .fetch.reddit_extractor import RedditThreadExtractor
from .output_format import format_answer_json, format_answer_text
from .pipeline import SearchPipeline
from .providers.reddit import REDDIT_SORTS, REDDIT_TIME_FILTERS, RedditProvider
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
    parser.add_argument("--provider", choices=("searxng", "reddit"), default=None)
    parser.add_argument("--engine", help="SearXNG engine name, for example `reddit` or `duckduckgo`.")
    parser.add_argument("--strategy", default=None)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument(
        "--reddit-url",
        help=f"Reddit base URL. Defaults to {DEFAULT_REDDIT_URL} or $REDDIT_BASE_URL.",
    )
    parser.add_argument("--subreddit", help="Restrict Reddit provider searches to one subreddit, e.g. `python`.")
    parser.add_argument("--reddit-sort", choices=sorted(REDDIT_SORTS), default=None)
    parser.add_argument("--reddit-time", choices=sorted(REDDIT_TIME_FILTERS), default=None)
    parser.add_argument("--reddit-comment-limit", type=int, default=None)
    parser.add_argument("--reddit-include-over-18", action="store_true")
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
    provider_name = (args.provider or config.search_provider).strip().lower()
    if provider_name not in {"searxng", "reddit"}:
        parser.exit(2, "Unknown provider. Valid options: searxng, reddit\n")

    base_url = args.searxng_url or config.searxng_url
    fetcher = None
    extractor = None
    if provider_name == "reddit":
        if args.engine:
            parser.exit(2, "--engine can only be used with --provider searxng.\n")
        reddit_base_url = args.reddit_url or config.reddit_base_url
        subreddit = args.subreddit or config.reddit_subreddit
        reddit_sort = args.reddit_sort or config.reddit_sort
        reddit_time = args.reddit_time or config.reddit_time
        reddit_comment_limit = args.reddit_comment_limit or config.reddit_comment_limit
        include_over_18 = args.reddit_include_over_18 or config.reddit_include_over_18
        try:
            provider = RedditProvider(
                base_url=reddit_base_url,
                subreddit=subreddit,
                sort=reddit_sort,
                time_filter=reddit_time,
                include_over_18=include_over_18,
                timeout=config.request_timeout,
                user_agent=config.user_agent,
                bearer_token=config.reddit_bearer_token,
            )
        except ValueError as exc:
            parser.exit(2, f"{exc}\n")
        fetcher = RedditThreadFetcher(
            timeout=config.request_timeout,
            user_agent=config.user_agent,
            comment_limit=reddit_comment_limit,
            bearer_token=config.reddit_bearer_token,
        )
        extractor = RedditThreadExtractor(
            max_comments=reddit_comment_limit,
            weak_text_threshold=config.weak_text_threshold,
            max_json_fetches=config.recovery_json_limit,
        )
    else:
        if args.engine:
            config.engine = args.engine
        provider = SearxngProvider(
            base_url=base_url,
            engine=config.engine,
            timeout=config.request_timeout,
            user_agent=config.user_agent,
        )

    strategy_name = args.strategy or ("reddit" if provider_name == "reddit" else "direct")
    pipeline = SearchPipeline(
        provider=provider,
        strategy=resolve_strategy(strategy_name),
        config=config,
        fetcher=fetcher,
        extractor=extractor,
    )
    try:
        answer = pipeline.run(args.question, limit_per_query=args.limit)
    except URLError as exc:
        if provider_name == "reddit":
            parser.exit(
                2,
                (
                    f"Could not reach Reddit at {args.reddit_url or config.reddit_base_url}.\n"
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


if __name__ == "__main__":
    main()
