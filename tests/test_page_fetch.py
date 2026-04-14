from __future__ import annotations

import unittest

from websearch_agents.output_format import format_page_document_json, format_page_document_text
from websearch_agents.page_fetch import fetch_page_document
from websearch_agents.types import PageDocument


class StubFetcher:
    def __init__(self, html: str):
        self.html = html

    def fetch(self, url: str) -> str:
        return self.html


class StubExtractor:
    def extract(self, url: str, html: str) -> PageDocument:
        return PageDocument(
            url=url,
            title="Stripe, Inc. - Wikipedia",
            text="Stripe is a financial infrastructure company. It was founded in 2010.",
            fetched_at="2026-01-01T00:00:00+00:00",
            published_at=None,
            extraction_method="stub",
        )


class PageFetchTests(unittest.TestCase):
    def test_fetch_page_document_reuses_fetcher_and_extractor(self) -> None:
        document = fetch_page_document(
            "https://example.com/stripe",
            fetcher=StubFetcher("<html></html>"),
            extractor=StubExtractor(),
        )

        self.assertEqual(document.title, "Stripe, Inc. - Wikipedia")
        self.assertEqual(document.extraction_method, "stub")

    def test_page_document_formats_cleanly(self) -> None:
        document = PageDocument(
            url="https://example.com/page",
            title="Example Page",
            text="One two three four five six.",
            fetched_at="2026-01-01T00:00:00+00:00",
            extraction_method="fallback",
        )

        text = format_page_document_text(document, max_chars=10)
        payload = format_page_document_json(document, max_chars=10)

        self.assertIn("PAGE", text)
        self.assertIn("TEXT", text)
        self.assertTrue(payload["result"]["text_truncated"])
        self.assertEqual(payload["kind"], "page_document")
        self.assertEqual(payload["result"]["word_count"], 6)


if __name__ == "__main__":
    unittest.main()
