from __future__ import annotations

from urllib.parse import parse_qs, urlparse
import unittest

from websearch_agents.fetch.reddit import RedditThreadFetcher, is_reddit_thread_url, reddit_thread_json_url


class FakeHeaders:
    def get_content_charset(self):
        return "utf-8"


class FakeResponse:
    headers = FakeHeaders()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self) -> bytes:
        return b"[]"


class RedditFetchTests(unittest.TestCase):
    def test_reddit_thread_urls_are_rewritten_to_json(self) -> None:
        url = "https://old.reddit.com/r/Python/comments/abc123/example_thread/?utm_source=share#comments"

        rewritten = reddit_thread_json_url(url, comment_limit=3, comment_sort="top")

        parsed = urlparse(rewritten)
        query = parse_qs(parsed.query)
        self.assertEqual(parsed.netloc, "www.reddit.com")
        self.assertEqual(parsed.path, "/r/Python/comments/abc123/example_thread.json")
        self.assertEqual(query["raw_json"], ["1"])
        self.assertEqual(query["limit"], ["3"])
        self.assertEqual(query["sort"], ["top"])
        self.assertNotIn("utm_source", query)
        self.assertTrue(is_reddit_thread_url(url))

    def test_fetcher_requests_reddit_json_endpoint(self) -> None:
        captured = {}

        def opener(request, timeout):
            captured["url"] = request.full_url
            captured["timeout"] = timeout
            captured["headers"] = dict(request.header_items())
            return FakeResponse()

        fetcher = RedditThreadFetcher(
            timeout=6,
            user_agent="test-agent",
            comment_limit=4,
            opener=opener,
        )

        text = fetcher.fetch("https://www.reddit.com/r/Python/comments/abc123/example_thread/")

        parsed = urlparse(captured["url"])
        query = parse_qs(parsed.query)
        self.assertEqual(text, "[]")
        self.assertEqual(parsed.path, "/r/Python/comments/abc123/example_thread.json")
        self.assertEqual(query["limit"], ["4"])
        self.assertEqual(captured["timeout"], 6)
        self.assertEqual(captured["headers"]["User-agent"], "test-agent")


if __name__ == "__main__":
    unittest.main()
