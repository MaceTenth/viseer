from __future__ import annotations

from datetime import UTC, datetime, timedelta
import unittest

from websearch_agents.ranking import domain_bonus, normalize_url, rank_documents, recency_bonus
from websearch_agents.types import PageDocument


class RankingTests(unittest.TestCase):
    def test_normalize_url_drops_fragment_and_tracking(self) -> None:
        raw = "https://Example.com/path/?utm_source=test&x=1#section"
        self.assertEqual(normalize_url(raw), "https://example.com/path?x=1")

    def test_trusted_recent_source_ranks_higher(self) -> None:
        today = datetime.now(UTC).date().isoformat()
        older = (datetime.now(UTC) - timedelta(days=500)).date().isoformat()
        docs = [
            PageDocument(
                url="https://agency.gov/briefing",
                title="Official briefing",
                text="Current wildfire update and containment status.",
                fetched_at=today,
                published_at=today,
                extraction_method="static",
            ),
            PageDocument(
                url="https://example.com/blog",
                title="Blog post",
                text="Current wildfire update and containment status.",
                fetched_at=today,
                published_at=older,
                extraction_method="static",
            ),
        ]

        ranked = rank_documents("current wildfire update", docs, recency_weight=1.0)
        self.assertEqual(ranked[0].title, "Official briefing")
        self.assertGreater(domain_bonus(docs[0].url), domain_bonus(docs[1].url))
        self.assertGreater(recency_bonus(today), recency_bonus(older))


if __name__ == "__main__":
    unittest.main()
