from __future__ import annotations

import json
from urllib.parse import parse_qs, urlparse
import unittest

from websearch_agents.providers.reddit import RedditProvider


class FakeResponse:
    def __init__(self, payload: dict):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


class RedditProviderTests(unittest.TestCase):
    def test_search_maps_reddit_listing_to_search_results(self) -> None:
        payload = {
            "data": {
                "children": [
                    {
                        "kind": "t3",
                        "data": {
                            "id": "abc123",
                            "name": "t3_abc123",
                            "title": "Good Python debugging tools?",
                            "permalink": "/r/Python/comments/abc123/good_python_debugging_tools/",
                            "selftext": "I am comparing debuggers and profilers.",
                            "subreddit": "Python",
                            "author": "example_user",
                            "score": 42,
                            "num_comments": 9,
                            "upvote_ratio": 0.94,
                            "created_utc": 1767225600,
                            "url": "https://www.reddit.com/r/Python/comments/abc123/good_python_debugging_tools/",
                            "over_18": False,
                        },
                    },
                    {
                        "kind": "t3",
                        "data": {
                            "title": "Filtered post",
                            "permalink": "/r/Python/comments/nsfw/filtered/",
                            "subreddit": "Python",
                            "over_18": True,
                        },
                    },
                ]
            }
        }
        captured = {}

        def opener(request, timeout):
            captured["url"] = request.full_url
            captured["timeout"] = timeout
            captured["headers"] = dict(request.header_items())
            return FakeResponse(payload)

        provider = RedditProvider(
            subreddit="r/Python",
            sort="top",
            time_filter="week",
            timeout=7,
            user_agent="test-agent",
            opener=opener,
        )

        results = provider.search("debugging tools", limit=5)

        parsed = urlparse(captured["url"])
        query = parse_qs(parsed.query)
        self.assertEqual(parsed.path, "/r/Python/search.json")
        self.assertEqual(query["q"], ["debugging tools"])
        self.assertEqual(query["restrict_sr"], ["1"])
        self.assertEqual(query["sort"], ["top"])
        self.assertEqual(query["t"], ["week"])
        self.assertEqual(captured["timeout"], 7)
        self.assertEqual(captured["headers"]["User-agent"], "test-agent")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].title, "Good Python debugging tools?")
        self.assertEqual(results[0].source, "reddit:r/Python")
        self.assertIn("debuggers and profilers", results[0].snippet)
        self.assertEqual(results[0].metadata["score"], 42)
        self.assertEqual(results[0].published_at, "2026-01-01T00:00:00+00:00")


if __name__ == "__main__":
    unittest.main()
