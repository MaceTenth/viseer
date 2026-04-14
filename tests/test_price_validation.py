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

    def test_ignores_shipping_fee_when_product_price_is_present(self) -> None:
        docs = [
            PageDocument(
                url="https://www.apple.com/shop/buy-mac/macbook-air",
                title="Buy MacBook Air - Apple",
                text=(
                    "MacBook Air 13-inch with M3 chip\n"
                    "$1,099.00\n"
                    "The two-hour delivery fee is $9. You'll choose a delivery date during checkout."
                ),
                fetched_at="2026-01-01T00:00:00+00:00",
            )
        ]

        prices = extract_price_evidence("MacBook Air M3 13-inch price", docs)

        self.assertEqual(len(prices), 1)
        self.assertEqual(prices[0].amount, 1099.0)

    def test_hardware_query_ignores_installment_price(self) -> None:
        docs = [
            PageDocument(
                url="https://www.apple.com/shop/buy-mac/macbook-air",
                title="Buy MacBook Air - Apple",
                text=(
                    "MacBook Air 13-inch with M3 chip\n"
                    "From $1,099.00 or $91.58 per month for 12 months\n"
                ),
                fetched_at="2026-01-01T00:00:00+00:00",
            )
        ]

        prices = extract_price_evidence("MacBook Air M3 13-inch price", docs)

        self.assertEqual(len(prices), 1)
        self.assertEqual(prices[0].amount, 1099.0)

    def test_prefers_plan_specific_match_over_generic_other_tier(self) -> None:
        docs = [
            PageDocument(
                url="https://content-whale.com/chatgpt-pricing",
                title="ChatGPT pricing",
                text="ChatGPT Team ($30/user/month), Plus ($20/month), Pro ($200/month).",
                fetched_at="2026-01-01T00:00:00+00:00",
            ),
            PageDocument(
                url="https://example.com/chatgpt-plus",
                title="ChatGPT plans compared",
                text="ChatGPT Plus is $20/month and worth paying for.",
                fetched_at="2026-01-01T00:00:00+00:00",
            ),
        ]

        prices = extract_price_evidence("ChatGPT Team pricing", docs)

        self.assertEqual(prices[0].amount, 30.0)
        self.assertIn("Team", prices[0].snippet)

    def test_rejects_free_tier_when_question_is_for_ai_pricing(self) -> None:
        docs = [
            PageDocument(
                url="https://www.notion.com/pricing",
                title="Notion pricing",
                text=(
                    "$0 per member / month\n"
                    "Includes trial AI capabilities.\n"
                    "Business plan $15 per member / month"
                ),
                fetched_at="2026-01-01T00:00:00+00:00",
            )
        ]

        prices = extract_price_evidence("Notion AI pricing", docs)

        self.assertEqual(prices, [])

    def test_supports_ils_prices(self) -> None:
        docs = [
            PageDocument(
                url="https://www.apple.com/il/macbook-air",
                title="MacBook Air - Apple",
                text="MacBook Air M3 13-inch\n₪4,999",
                fetched_at="2026-01-01T00:00:00+00:00",
            )
        ]

        prices = extract_price_evidence("MacBook Air M3 13-inch price", docs)

        self.assertEqual(len(prices), 1)
        self.assertEqual(prices[0].currency, "ILS")
        self.assertEqual(prices[0].amount, 4999.0)

    def test_rejects_secondary_market_listing_when_query_is_generic(self) -> None:
        docs = [
            PageDocument(
                url="https://www.amazon.com/example-product",
                title="MacBook Air M3 13-inch (Renewed)",
                text="Renewed MacBook Air M3 13-inch for $799.",
                fetched_at="2026-01-01T00:00:00+00:00",
            )
        ]

        prices = extract_price_evidence("MacBook Air M3 13-inch price", docs)

        self.assertEqual(prices, [])


if __name__ == "__main__":
    unittest.main()
