from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from websearch_agents.config import DEFAULT_SEARXNG_URL, PipelineConfig


class ConfigTests(unittest.TestCase):
    def test_env_defaults_to_local_searxng_url(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            config = PipelineConfig.from_env()

        self.assertEqual(config.searxng_url, DEFAULT_SEARXNG_URL)


if __name__ == "__main__":
    unittest.main()
