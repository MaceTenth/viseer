from __future__ import annotations

from urllib.request import Request, urlopen


class HttpFetcher:
    def __init__(self, timeout: float = 20.0, user_agent: str = "viseer/0.1"):
        self.timeout = timeout
        self.user_agent = user_agent

    def fetch(self, url: str) -> str:
        request = Request(
            url,
            headers={
                "User-Agent": self.user_agent,
                "Accept": "text/html,application/xhtml+xml,text/plain;q=0.9,*/*;q=0.8",
            },
        )
        with urlopen(request, timeout=self.timeout) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            return response.read().decode(charset, errors="replace")
