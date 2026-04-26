from __future__ import annotations

from datetime import UTC, datetime, timedelta
import unittest

from websearch_agents.ranking import (
    discover_preferred_domain_families,
    domain_bonus,
    normalize_url,
    rank_documents,
    recency_bonus,
)
from websearch_agents.types import PageDocument, SearchResult


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

    def test_discovers_likely_official_domains_from_results(self) -> None:
        results = [
            SearchResult(
                title="OpenAI Pricing",
                url="https://openai.com/api/pricing/",
                snippet="Official pricing page.",
                source="mock",
            ),
            SearchResult(
                title="Anthropic API pricing",
                url="https://docs.anthropic.com/en/docs/about-claude/pricing",
                snippet="Pricing docs.",
                source="mock",
            ),
            SearchResult(
                title="Third-party comparison",
                url="https://example.com/openai-vs-anthropic-pricing",
                snippet="OpenAI and Anthropic pricing compared.",
                source="mock",
            ),
        ]

        preferred = discover_preferred_domain_families("OpenAI vs Anthropic pricing", results)

        self.assertIn("openai.com", preferred)
        self.assertIn("anthropic.com", preferred)
        self.assertNotIn("example.com", preferred)

    def test_ranking_prefers_official_source_over_social_profile(self) -> None:
        docs = [
            PageDocument(
                url="https://www.linkedin.com/in/satyanadella",
                title="Satya Nadella - Chairman and CEO at Microsoft | LinkedIn",
                text="Satya Nadella is the Chairman and CEO of Microsoft.",
                fetched_at="2026-01-01T00:00:00+00:00",
                extraction_method="static",
            ),
            PageDocument(
                url="https://news.microsoft.com/source/exec/satya-nadella/",
                title="Satya Nadella - Microsoft",
                text="Satya Nadella is Chairman and CEO of Microsoft.",
                fetched_at="2026-01-01T00:00:00+00:00",
                extraction_method="static",
            ),
        ]

        ranked = rank_documents(
            "Who is the current CEO of Microsoft?",
            docs,
            recency_weight=1.0,
            strategy_name="latest_info",
            preferred_domain_families={"microsoft.com"},
        )

        self.assertEqual(ranked[0].url, "https://news.microsoft.com/source/exec/satya-nadella/")
        self.assertIn("official", ranked[0].metadata["source_types"])
        self.assertIn("social", ranked[1].metadata["source_types"])

    def test_community_strategy_boosts_reddit_sources(self) -> None:
        docs = [
            PageDocument(
                url="https://www.reddit.com/r/framework/comments/abc123/thread/",
                title="Framework laptop long term experience",
                text="Several users discuss repairability, battery life, and Linux support.",
                fetched_at="2026-01-01T00:00:00+00:00",
                extraction_method="reddit_json",
            )
        ]

        ranked = rank_documents(
            "Framework laptop experience",
            docs,
            strategy_name="community_discussion",
        )

        self.assertIn("community", ranked[0].metadata["source_types"])
        self.assertIn("community-source signal", ranked[0].metadata["ranking_reasons"])
        self.assertGreater(ranked[0].score, 0)


if __name__ == "__main__":
    unittest.main()
