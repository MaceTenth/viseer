from __future__ import annotations

import unittest

from websearch_agents.synthesis import build_citations, render_answer
from websearch_agents.types import Evidence


class SynthesisTests(unittest.TestCase):
    def test_citations_capture_quote_and_access_time(self) -> None:
        evidence = [
            Evidence(
                url="https://example.com/article",
                title="Example",
                quote="Quoted text.",
                summary="Summary.",
                score=3.0,
                published_at="2026-04-01",
            )
        ]

        citations = build_citations(evidence)

        self.assertEqual(citations[0].quote, "Quoted text.")
        self.assertEqual(citations[0].published_at, "2026-04-01")
        self.assertIsNotNone(citations[0].accessed_at)
        self.assertIn("Example", render_answer("question", evidence, "direct_lookup"))


if __name__ == "__main__":
    unittest.main()
