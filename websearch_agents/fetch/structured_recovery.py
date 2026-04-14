from __future__ import annotations

import html as html_lib
import json
import re
from urllib.parse import urljoin, urlparse


_META_TAG_RE = re.compile(r"<meta\b([^>]+)>", re.IGNORECASE)
_ATTR_RE = re.compile(r'([a-zA-Z_:.-]+)\s*=\s*([\'"])(.*?)\2', re.DOTALL)
_JSON_LD_RE = re.compile(
    r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
    re.IGNORECASE | re.DOTALL,
)
_NEXT_DATA_RE = re.compile(
    r'<script[^>]+id=["\']__NEXT_DATA__["\'][^>]*>(.*?)</script>',
    re.IGNORECASE | re.DOTALL,
)
_QUOTED_ENDPOINT_RE = re.compile(
    r'["\']([^"\']*(?:\.json(?:\?[^"\']*)?|/(?:api|_next/data|wp-json)[^"\']*))["\']',
    re.IGNORECASE,
)
_WHITESPACE_RE = re.compile(r"\s+")
_TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)
_JSON_KEYS_TO_SKIP = {
    "@context",
    "@id",
    "@type",
    "__typename",
    "csrf",
    "id",
    "nonce",
    "token",
    "uuid",
}
_META_FIELD_MAP = {
    "description": "description",
    "keywords": "keywords",
    "og:description": "description",
    "og:title": "title",
    "twitter:description": "description",
    "twitter:title": "title",
}
_HYDRATION_TOKENS = (
    "__NUXT__",
    "__APOLLO_STATE__",
    "__INITIAL_STATE__",
    "__PRELOADED_STATE__",
)


def _normalize_space(value: str) -> str:
    return _WHITESPACE_RE.sub(" ", value).strip()


def _append_unique(items: list[str], value: str) -> None:
    if value and value not in items:
        items.append(value)


def _extract_title(html: str) -> str:
    match = _TITLE_RE.search(html)
    if not match:
        return ""
    return _normalize_space(html_lib.unescape(match.group(1)))


def _parse_attrs(raw: str) -> dict[str, str]:
    attrs: dict[str, str] = {}
    for key, _, value in _ATTR_RE.findall(raw):
        attrs[key.lower()] = html_lib.unescape(value)
    return attrs


def _extract_meta_text(html: str, title: str = "") -> str:
    values: dict[str, str] = {}

    for raw_attrs in _META_TAG_RE.findall(html):
        attrs = _parse_attrs(raw_attrs)
        key = (attrs.get("property") or attrs.get("name") or "").lower()
        label = _META_FIELD_MAP.get(key)
        content = _normalize_space(attrs.get("content", ""))
        if label and content and label not in values:
            values[label] = content

    lines = [f"{label}: {content}" for label, content in values.items() if content]
    return "\n".join(lines)


def _extract_balanced_json(value: str, start: int) -> str | None:
    if start < 0 or start >= len(value):
        return None
    opening = value[start]
    closing = "}" if opening == "{" else "]"
    depth = 0
    in_string = False
    escape = False

    for index in range(start, len(value)):
        char = value[index]
        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == in_string:
                in_string = False
            continue
        if char in {'"', "'"}:
            in_string = char
            continue
        if char == opening:
            depth += 1
        elif char == closing:
            depth -= 1
            if depth == 0:
                return value[start : index + 1]
    return None


def _load_json(raw: str) -> object | None:
    candidate = html_lib.unescape(raw).strip()
    if not candidate:
        return None
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        return None


def _looks_like_noise(value: str) -> bool:
    compact = value.strip()
    if not compact:
        return True
    if compact.startswith(("http://", "https://")) and len(compact) > 60:
        return True
    if len(compact) > 220 and " " not in compact:
        return True
    return False


def _flatten_json(value: object, output: list[str], *, prefix: str = "", limit: int = 80) -> None:
    if len(output) >= limit:
        return

    if isinstance(value, dict):
        for key, item in value.items():
            if str(key).lower() in _JSON_KEYS_TO_SKIP:
                continue
            clean_key = str(key).replace("_", " ").strip()
            next_prefix = clean_key if not prefix else f"{prefix} {clean_key}".strip()
            _flatten_json(item, output, prefix=next_prefix, limit=limit)
            if len(output) >= limit:
                return
        return

    if isinstance(value, list):
        for item in value[:12]:
            _flatten_json(item, output, prefix=prefix, limit=limit)
            if len(output) >= limit:
                return
        return

    if isinstance(value, bool) or value is None:
        return

    text = _normalize_space(str(value))
    if not text or _looks_like_noise(text):
        return
    line = f"{prefix}: {text}" if prefix else text
    if line not in output:
        output.append(line)


def _json_to_text(value: object) -> str:
    lines: list[str] = []
    _flatten_json(value, lines)
    return "\n".join(lines)


def _extract_json_ld(html: str, attempts: list[dict[str, str]]) -> tuple[str, list[str]]:
    sections: list[str] = []
    sources: list[str] = []
    count = 0
    for raw_block in _JSON_LD_RE.findall(html):
        payload = _load_json(raw_block)
        if payload is None:
            continue
        text = _json_to_text(payload)
        if text:
            sections.append(text)
            count += 1
    attempts.append(
        {
            "kind": "json_ld",
            "status": "recovered" if count else "not_found",
        }
    )
    if count:
        sources.append("json_ld")
    return "\n\n".join(sections), sources


def _extract_hydration_payloads(html: str, attempts: list[dict[str, str]]) -> tuple[str, list[str]]:
    sections: list[str] = []
    sources: list[str] = []
    found = False

    for raw_block in _NEXT_DATA_RE.findall(html):
        payload = _load_json(raw_block)
        if payload is None:
            continue
        text = _json_to_text(payload)
        if text:
            sections.append(text)
            found = True

    for token in _HYDRATION_TOKENS:
        search_from = 0
        while True:
            index = html.find(token, search_from)
            if index == -1:
                break
            equals_index = html.find("=", index)
            if equals_index == -1:
                break
            start = -1
            for char in "{[":
                position = html.find(char, equals_index)
                if position != -1 and (start == -1 or position < start):
                    start = position
            if start == -1:
                break
            payload = _load_json(_extract_balanced_json(html, start) or "")
            if payload is not None:
                text = _json_to_text(payload)
                if text:
                    sections.append(text)
                    found = True
                    break
            search_from = start + 1

    attempts.append(
        {
            "kind": "hydration",
            "status": "recovered" if found else "not_found",
        }
    )
    if found:
        sources.append("hydration")
    return "\n\n".join(sections), sources


def _looks_like_json_endpoint(path: str) -> bool:
    lowered = path.lower()
    return (
        lowered.endswith(".json")
        or lowered.startswith("/api/")
        or "/api/" in lowered
        or "/_next/data/" in lowered
        or "/wp-json/" in lowered
    )


def _discover_json_endpoints(url: str, html: str) -> list[str]:
    parsed_url = urlparse(url)
    seen: set[str] = set()
    endpoints: list[str] = []

    for raw in _QUOTED_ENDPOINT_RE.findall(html):
        candidate = html_lib.unescape(raw).strip()
        if not candidate:
            continue
        resolved = urljoin(url, candidate)
        parsed_candidate = urlparse(resolved)
        if parsed_candidate.scheme not in {"http", "https"}:
            continue
        if parsed_candidate.netloc != parsed_url.netloc:
            continue
        if not _looks_like_json_endpoint(parsed_candidate.path):
            continue
        if resolved in seen:
            continue
        seen.add(resolved)
        endpoints.append(resolved)
    return endpoints


def _extract_api_json(
    *,
    url: str,
    html: str,
    fetcher,
    attempts: list[dict[str, str]],
    max_json_fetches: int,
) -> tuple[str, list[str]]:
    if fetcher is None or max_json_fetches <= 0:
        attempts.append({"kind": "api_json", "status": "skipped"})
        return "", []

    sections: list[str] = []
    sources: list[str] = []
    endpoints = _discover_json_endpoints(url, html)[:max_json_fetches]
    if not endpoints:
        attempts.append({"kind": "api_json", "status": "not_found"})
        return "", []

    for endpoint in endpoints:
        try:
            payload = _load_json(fetcher.fetch(endpoint))
        except Exception as exc:  # pragma: no cover - error path exercised through integration tests
            attempts.append({"kind": "api_json", "status": "error", "url": endpoint, "error": str(exc)})
            continue
        if payload is None:
            attempts.append({"kind": "api_json", "status": "non_json", "url": endpoint})
            continue
        text = _json_to_text(payload)
        if not text:
            attempts.append({"kind": "api_json", "status": "empty", "url": endpoint})
            continue
        sections.append(text)
        attempts.append({"kind": "api_json", "status": "success", "url": endpoint})
        _append_unique(sources, "api_json")

    return "\n\n".join(sections), sources


def detect_dynamic_signals(html: str) -> list[str]:
    lowered = html.lower()
    signals: list[str] = []

    checks = (
        ("id=\"__next\"", "next_root"),
        ("id='__next'", "next_root"),
        ("window.__nuxt__", "nuxt_state"),
        ("data-reactroot", "react_root"),
        ("__apollo_state__", "apollo_state"),
        ("__initial_state__", "initial_state"),
        ("__preloaded_state__", "preloaded_state"),
        ("fetch(", "script_fetch_calls"),
        ("axios.get(", "script_fetch_calls"),
        ("xmlhttprequest", "xhr_usage"),
    )
    for needle, label in checks:
        if needle in lowered:
            _append_unique(signals, label)

    if lowered.count("<script") >= 5:
        _append_unique(signals, "script_heavy")
    if re.search(r"<div[^>]+id=[\"'](?:__next|root|app)[\"'][^>]*>\s*</div>", lowered):
        _append_unique(signals, "empty_app_shell")
    return signals


def recover_structured_text(
    *,
    url: str,
    html: str,
    fetcher=None,
    title: str = "",
    max_json_fetches: int = 2,
) -> dict[str, object]:
    attempts: list[dict[str, str]] = []
    sections: list[str] = []
    structured_sources: list[str] = []
    dynamic_signals = detect_dynamic_signals(html)

    meta_text = _extract_meta_text(html, title=title)
    if meta_text:
        sections.append(meta_text)
        structured_sources.append("metadata")
        attempts.append({"kind": "metadata", "status": "recovered"})
    else:
        attempts.append({"kind": "metadata", "status": "not_found"})

    json_ld_text, json_ld_sources = _extract_json_ld(html, attempts)
    if json_ld_text:
        sections.append(json_ld_text)
    for source in json_ld_sources:
        _append_unique(structured_sources, source)

    hydration_text, hydration_sources = _extract_hydration_payloads(html, attempts)
    if hydration_text:
        sections.append(hydration_text)
    for source in hydration_sources:
        _append_unique(structured_sources, source)

    api_text, api_sources = _extract_api_json(
        url=url,
        html=html,
        fetcher=fetcher,
        attempts=attempts,
        max_json_fetches=max_json_fetches,
    )
    if api_text:
        sections.append(api_text)
    for source in api_sources:
        _append_unique(structured_sources, source)

    combined_text = "\n\n".join(section for section in sections if section).strip()
    recovery_failed = bool(dynamic_signals) and not combined_text
    return {
        "text": combined_text,
        "structured_sources": structured_sources,
        "dynamic_signals": dynamic_signals,
        "recovery_attempts": attempts,
        "recovery_failed": recovery_failed,
    }
