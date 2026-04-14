from __future__ import annotations

import unittest

from websearch_agents.price_validation import extract_price_evidence, validate_price_consensus
from websearch_agents.types import PageDocument


class PriceValidationTests(unittest.TestCase):
    def test_extracts_one_best_price_per_domain(self) -> None:
        docs = [
            PageDocument(
                url="https://store.example.com/product",
                title="Example Store",
                text="Buy now. Price $1,299. MSRP $1,399.",
                fetched_at="2026-01-01T00:00:00+00:00",
            )
        ]

        prices = extract_price_evidence("Example laptop price", docs)

        self.assertEqual(len(prices), 1)
        self.assertEqual(prices[0].currency, "USD")
        self.assertEqual(prices[0].amount, 1299.0)

    def test_supported_verdict_when_three_domains_agree(self) -> None:
        docs = [
            PageDocument(
                url="https://store-a.example.com/product",
                title="Store A",
                text="Current price: $1,299. Buy today.",
                fetched_at="2026-01-01T00:00:00+00:00",
            ),
            PageDocument(
                url="https://store-b.example.com/product",
                title="Store B",
                text="Official price USD 1299.",
                fetched_at="2026-01-01T00:00:00+00:00",
            ),
            PageDocument(
                url="https://store-c.example.com/product",
                title="Store C",
                text="Starting at $1,299 for the base model.",
                fetched_at="2026-01-01T00:00:00+00:00",
            ),
            PageDocument(
                url="https://store-d.example.com/product",
                title="Store D",
                text="Sale price $1,499.",
                fetched_at="2026-01-01T00:00:00+00:00",
            ),
        ]

        result = validate_price_consensus("Example laptop price", docs, min_sources=3)

        self.assertEqual(result.verdict, "supported")
        self.assertEqual(result.consensus_currency, "USD")
        self.assertEqual(result.consensus_amount, 1299.0)
        self.assertEqual(len(result.agreeing), 3)
        self.assertEqual(len(result.conflicting), 1)


if __name__ == "__main__":
    unittest.main()
