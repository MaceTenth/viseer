from __future__ import annotations

import unittest

from websearch_agents.config import PipelineConfig
from websearch_agents.pipeline import SearchPipeline
from websearch_agents.providers.mock import MockProvider
from websearch_agents.strategies import VerifyClaimStrategy
from websearch_agents.types import PageDocument, SearchResult


class StaticFetcher:
    def __init__(self, pages: dict[str, str]):
        self.pages = pages

    def fetch(self, url: str) -> str:
        return self.pages[url]


class StaticExtractor:
    def extract(self, url: str, html: str) -> PageDocument:
        return PageDocument(
            url=url,
            title="",
            text=html,
            fetched_at="2026-01-01T00:00:00+00:00",
            extraction_method="static",
        )


class PipelineTests(unittest.TestCase):
    def test_pipeline_returns_traceable_answer(self) -> None:
        provider = MockProvider(
            {
                'vaccines cause autism': [
                    SearchResult(
                        title="CDC",
                        url="https://www.cdc.gov/vaccinesafety/concerns/autism.html",
                        snippet="Studies show no link.",
                        source="mock",
                    ),
                    SearchResult(
                        title="WHO",
                        url="https://www.who.int/news-room/questions-and-answers/item/vaccines-and-autism",
                        snippet="No evidence supports the claim.",
                        source="mock",
                    ),
                ],
                '"vaccines cause autism"': [],
                "vaccines cause autism fact check": [],
                "vaccines cause autism official statement": [],
            }
        )
        fetcher = StaticFetcher(
            {
                "https://www.cdc.gov/vaccinesafety/concerns/autism.html": (
                    "Vaccines do not cause autism. Large studies have found no link."
                ),
                "https://www.who.int/news-room/questions-and-answers/item/vaccines-and-autism": (
                    "There is no evidence that vaccines cause autism or autism spectrum disorders."
                ),
            }
        )
        pipeline = SearchPipeline(
            provider=provider,
            strategy=VerifyClaimStrategy(),
            config=PipelineConfig(max_evidence=3),
            fetcher=fetcher,
            extractor=StaticExtractor(),
        )

        answer = pipeline.run("vaccines cause autism")

        self.assertEqual(answer.strategy, "verify_claim")
        self.assertEqual(len(answer.citations), 2)
        self.assertIn("Collected 2 evidence item(s)", answer.answer)
        self.assertEqual(answer.trace.pages_fetched, 2)
        self.assertEqual(answer.trace.pages_extracted, 2)
        self.assertEqual(answer.trace.queries[0].query, "vaccines cause autism")


if __name__ == "__main__":
    unittest.main()
