from __future__ import annotations

import argparse
import json
import sys
from urllib.error import URLError

from .config import PipelineConfig
from .fetch.http_fetcher import HttpFetcher
from .fetch.trafilatura_extractor import TrafilaturaExtractor
from .output_format import format_page_document_json, format_page_document_text
from .rich_output import (
    RICH_INSTALL_MESSAGE,
    print_json_rich,
    print_page_document_rich,
    rich_available,
    should_use_rich,
)
from .types import PageDocument


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Viseer fetch: extract structured text from a single web page."
    )
    parser.add_argument("url", help="Page URL to fetch and extract.")
    parser.add_argument(
        "--max-chars",
        type=int,
        default=None,
        help="Maximum number of extracted text characters to include in the output.",
    )
    parser.add_argument("--json", action="store_true", dest="as_json")
    style_group = parser.add_mutually_exclusive_group()
    style_group.add_argument(
        "--rich",
        action="store_true",
        help="Force Rich output. Requires `pip install -e '.[ui]'`.",
    )
    style_group.add_argument(
        "--plain",
        action="store_true",
        help="Disable Rich output even when it is available.",
    )
    return parser


def fetch_page_document(
    url: str,
    *,
    config: PipelineConfig | None = None,
    fetcher: HttpFetcher | None = None,
    extractor: TrafilaturaExtractor | None = None,
) -> PageDocument:
    config = config or PipelineConfig.from_env()
    fetcher = fetcher or HttpFetcher(
        timeout=config.request_timeout,
        user_agent=config.user_agent,
    )
    extractor = extractor or TrafilaturaExtractor()

    html = fetcher.fetch(url)
    document = extractor.extract(url, html)
    if document is None:
        raise ValueError(f"Could not extract readable text from {url}")
    if not document.title:
        document.title = url
    return document


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    try:
        document = fetch_page_document(args.url)
    except URLError as exc:
        parser.exit(2, f"Could not fetch {args.url}.\nOriginal error: {exc}\n")
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
        payload = format_page_document_json(document, max_chars=args.max_chars)
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
            print_page_document_rich(document, max_chars=args.max_chars or 4000)
        except RuntimeError:
            parser.exit(2, f"{RICH_INSTALL_MESSAGE}\n")
        return

    print(format_page_document_text(document, max_chars=args.max_chars or 4000))


if __name__ == "__main__":
    main()
