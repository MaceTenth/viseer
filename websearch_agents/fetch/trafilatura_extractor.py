from __future__ import annotations

from datetime import UTC, datetime
import html as html_lib
import re

from ..types import PageDocument
from .structured_recovery import recover_structured_text

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
    def __init__(self, *, weak_text_threshold: int = 400, max_json_fetches: int = 2):
        self.weak_text_threshold = weak_text_threshold
        self.max_json_fetches = max_json_fetches

    def extract(self, url: str, html: str, fetcher=None) -> PageDocument | None:
        text = ""
        method = "fallback"
        title = _extract_title(html)
        published_at = _extract_published_at(html)
        metadata = {
            "structured_sources": [],
            "dynamic_signals": [],
            "recovery_attempts": [],
            "recovery_failed": False,
        }

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

        recovery = None
        if len(text.strip()) < self.weak_text_threshold:
            recovery = recover_structured_text(
                url=url,
                html=html,
                fetcher=fetcher,
                title=title,
                max_json_fetches=self.max_json_fetches,
            )
            metadata.update(recovery)
            recovered_text = str(recovery.get("text", "")).strip()
            if recovered_text:
                base_text = text.strip()
                base_is_insubstantial = not base_text or base_text == title or len(base_text) < 80
                if base_text and not base_is_insubstantial:
                    if recovered_text not in base_text:
                        text = "\n\n".join(part for part in (text.strip(), recovered_text) if part)
                    method = "hybrid"
                else:
                    text = recovered_text
                    sources = metadata.get("structured_sources") or []
                    method = sources[0] if len(sources) == 1 else "hybrid"
            elif metadata["recovery_failed"] and not text:
                text = title

        if not text and not title and not metadata["dynamic_signals"]:
            return None

        return PageDocument(
            url=url,
            title=title,
            text=text,
            fetched_at=datetime.now(UTC).isoformat(),
            published_at=published_at,
            extraction_method=method,
            metadata=metadata,
        )
