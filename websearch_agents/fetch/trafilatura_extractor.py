from __future__ import annotations

from datetime import UTC, datetime
import html as html_lib
import re

from ..types import PageDocument

try:
    import trafilatura as _trafilatura
except ImportError:  # pragma: no cover - optional dependency
    _trafilatura = None


_TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)
_TAG_RE = re.compile(r"<[^>]+>")
_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
_SCRIPT_STYLE_RE = re.compile(
    r"<(script|style|noscript)[^>]*>.*?</\1>",
    re.IGNORECASE | re.DOTALL,
)
_DATE_PATTERNS = [
    re.compile(
        r'<meta[^>]+(?:property|name)=["\'](?:article:published_time|og:published_time|pubdate|date)["\'][^>]+content=["\']([^"\']+)["\']',
        re.IGNORECASE,
    ),
    re.compile(
        r'<time[^>]+datetime=["\']([^"\']+)["\']',
        re.IGNORECASE,
    ),
]


def _normalize_space(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _extract_title(html: str) -> str:
    match = _TITLE_RE.search(html)
    if not match:
        return ""
    return _normalize_space(html_lib.unescape(match.group(1)))


def _extract_published_at(html: str) -> str | None:
    for pattern in _DATE_PATTERNS:
        match = pattern.search(html)
        if match:
            return match.group(1).strip()
    return None


def _fallback_extract_text(html: str) -> str:
    html = _SCRIPT_STYLE_RE.sub(" ", html)
    html = _COMMENT_RE.sub(" ", html)
    html = _TAG_RE.sub(" ", html)
    html = html_lib.unescape(html)
    return _normalize_space(html)


class TrafilaturaExtractor:
    def extract(self, url: str, html: str) -> PageDocument | None:
        text = ""
        method = "fallback"

        if _trafilatura is not None:
            text = _trafilatura.extract(
                html,
                include_links=False,
                include_formatting=False,
                favor_precision=True,
            ) or ""
            method = "trafilatura" if text else method

        if not text:
            text = _fallback_extract_text(html)

        if not text:
            return None

        return PageDocument(
            url=url,
            title=_extract_title(html),
            text=text,
            fetched_at=datetime.now(UTC).isoformat(),
            published_at=_extract_published_at(html),
            extraction_method=method,
        )
