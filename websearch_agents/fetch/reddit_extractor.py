from __future__ import annotations

from datetime import UTC, datetime
import html
import json
import re
from typing import Any

from ..types import PageDocument
from .reddit import is_reddit_thread_url
from .trafilatura_extractor import TrafilaturaExtractor


def _clean(value: Any) -> str:
    text = html.unescape(str(value or ""))
    return re.sub(r"\s+", " ", text).strip()


def _listing_children(listing: Any) -> list[dict[str, Any]]:
    if not isinstance(listing, dict):
        return []
    data = listing.get("data")
    if not isinstance(data, dict):
        return []
    children = data.get("children")
    if not isinstance(children, list):
        return []
    return [item for item in children if isinstance(item, dict)]


def _thing_data(child: dict[str, Any], kind: str) -> dict[str, Any] | None:
    if child.get("kind") != kind:
        return None
    data = child.get("data")
    return data if isinstance(data, dict) else None


def _published_at(data: dict[str, Any]) -> str | None:
    value = data.get("created_utc")
    if not isinstance(value, int | float):
        return None
    return datetime.fromtimestamp(value, UTC).isoformat()


def _collect_comments(children: list[dict[str, Any]], *, max_comments: int) -> list[dict[str, Any]]:
    comments: list[dict[str, Any]] = []

    def visit(items: list[dict[str, Any]]) -> None:
        for child in items:
            if len(comments) >= max_comments:
                return
            data = _thing_data(child, "t1")
            if data is None:
                continue

            body = _clean(data.get("body"))
            if body and body not in {"[deleted]", "[removed]"}:
                comments.append(
                    {
                        "author": data.get("author"),
                        "score": data.get("score"),
                        "body": body,
                        "id": data.get("id"),
                        "permalink": data.get("permalink"),
                    }
                )

            replies = data.get("replies")
            if isinstance(replies, dict):
                visit(_listing_children(replies))

    visit(children)
    return comments


class RedditThreadExtractor(TrafilaturaExtractor):
    def __init__(
        self,
        *,
        max_comments: int = 8,
        weak_text_threshold: int = 400,
        max_json_fetches: int = 2,
    ):
        super().__init__(
            weak_text_threshold=weak_text_threshold,
            max_json_fetches=max_json_fetches,
        )
        self.max_comments = max_comments

    def extract(self, url: str, html: str, fetcher=None) -> PageDocument | None:
        if not is_reddit_thread_url(url):
            return super().extract(url, html, fetcher=fetcher)

        try:
            payload = json.loads(html)
        except json.JSONDecodeError:
            return super().extract(url, html, fetcher=fetcher)

        if not isinstance(payload, list) or not payload:
            return super().extract(url, html, fetcher=fetcher)

        post_data = None
        for child in _listing_children(payload[0]):
            post_data = _thing_data(child, "t3")
            if post_data is not None:
                break
        if post_data is None:
            return super().extract(url, html, fetcher=fetcher)

        title = _clean(post_data.get("title")) or url
        selftext = _clean(post_data.get("selftext"))
        comments = _collect_comments(
            _listing_children(payload[1]) if len(payload) > 1 else [],
            max_comments=self.max_comments,
        )

        lines = [
            f"Reddit thread: {title}",
            f"Subreddit: r/{post_data.get('subreddit')}",
            f"Author: u/{post_data.get('author')}",
            f"Score: {post_data.get('score')}",
            f"Comments: {post_data.get('num_comments')}",
        ]
        original_url = _clean(post_data.get("url_overridden_by_dest") or post_data.get("url"))
        if original_url and original_url != url:
            lines.append(f"Linked URL: {original_url}")
        if selftext:
            lines.extend(["", "Post body:", selftext])
        if comments:
            lines.extend(["", "Top comments:"])
            for comment in comments:
                author = comment.get("author") or "unknown"
                score = comment.get("score")
                lines.append(f"u/{author} ({score} points): {comment['body']}")

        return PageDocument(
            url=url,
            title=title,
            text="\n".join(lines),
            fetched_at=datetime.now(UTC).isoformat(),
            published_at=_published_at(post_data),
            extraction_method="reddit_json",
            metadata={
                "structured_sources": ["reddit_json"],
                "dynamic_signals": [],
                "recovery_attempts": [],
                "recovery_failed": False,
                "provider": "reddit",
                "subreddit": post_data.get("subreddit"),
                "author": post_data.get("author"),
                "score": post_data.get("score"),
                "num_comments": post_data.get("num_comments"),
                "upvote_ratio": post_data.get("upvote_ratio"),
                "original_url": original_url,
                "top_comments": comments,
            },
        )
