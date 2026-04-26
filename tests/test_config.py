from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from websearch_agents.config import DEFAULT_REDDIT_URL, DEFAULT_SEARXNG_URL, PipelineConfig


class ConfigTests(unittest.TestCase):
    def test_env_defaults_to_local_searxng_url(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            config = PipelineConfig.from_env()

        self.assertEqual(config.searxng_url, DEFAULT_SEARXNG_URL)
        self.assertEqual(config.search_provider, "searxng")
        self.assertEqual(config.reddit_base_url, DEFAULT_REDDIT_URL)

    def test_env_reads_reddit_options(self) -> None:
        with patch.dict(
            os.environ,
            {
                "SEARCH_PROVIDER": "reddit",
                "REDDIT_SUBREDDIT": "Python",
                "REDDIT_SORT": "top",
                "REDDIT_TIME": "year",
                "REDDIT_INCLUDE_OVER_18": "true",
                "REDDIT_COMMENT_LIMIT": "3",
                "REDDIT_BEARER_TOKEN": "token",
            },
            clear=True,
        ):
            config = PipelineConfig.from_env()

        self.assertEqual(config.search_provider, "reddit")
        self.assertEqual(config.reddit_subreddit, "Python")
        self.assertEqual(config.reddit_sort, "top")
        self.assertEqual(config.reddit_time, "year")
        self.assertTrue(config.reddit_include_over_18)
        self.assertEqual(config.reddit_comment_limit, 3)
        self.assertEqual(config.reddit_bearer_token, "token")


if __name__ == "__main__":
    unittest.main()
