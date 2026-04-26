from __future__ import annotations

import json
import unittest

from websearch_agents.fetch.reddit_extractor import RedditThreadExtractor


class RedditExtractorTests(unittest.TestCase):
    def test_extracts_post_and_top_comments_from_thread_json(self) -> None:
        payload = [
            {
                "data": {
                    "children": [
                        {
                            "kind": "t3",
                            "data": {
                                "title": "Framework laptop long term experience",
                                "selftext": "I have used it for a year and the repairability is excellent.",
                                "subreddit": "Framework",
                                "author": "reviewer",
                                "score": 120,
                                "num_comments": 33,
                                "upvote_ratio": 0.91,
                                "created_utc": 1767225600,
                                "url": "https://www.reddit.com/r/framework/comments/abc123/thread/",
                            },
                        }
                    ]
                }
            },
            {
                "data": {
                    "children": [
                        {
                            "kind": "t1",
                            "data": {
                                "author": "commenter",
                                "score": 18,
                                "body": "The keyboard is solid, but battery life depends on the module.",
                                "id": "c1",
                                "permalink": "/r/framework/comments/abc123/thread/c1/",
                            },
                        }
                    ]
                }
            },
        ]

        extractor = RedditThreadExtractor(max_comments=2)
        doc = extractor.extract(
            "https://www.reddit.com/r/framework/comments/abc123/thread/",
            json.dumps(payload),
        )

        self.assertIsNotNone(doc)
        assert doc is not None
        self.assertEqual(doc.extraction_method, "reddit_json")
        self.assertEqual(doc.title, "Framework laptop long term experience")
        self.assertEqual(doc.published_at, "2026-01-01T00:00:00+00:00")
        self.assertIn("repairability is excellent", doc.text)
        self.assertIn("battery life depends", doc.text)
        self.assertEqual(doc.metadata["provider"], "reddit")
        self.assertEqual(doc.metadata["subreddit"], "Framework")
        self.assertEqual(doc.metadata["top_comments"][0]["author"], "commenter")


if __name__ == "__main__":
    unittest.main()
