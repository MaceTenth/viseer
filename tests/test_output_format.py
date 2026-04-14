from __future__ import annotations

import unittest

from websearch_agents.output_format import (
    format_answer_json,
    format_answer_text,
    format_price_result_json,
    format_price_result_text,
)
from websearch_agents.price_validation import PriceConsensusResult, PriceEvidence
from websearch_agents.types import Answer, AnswerTrace, Citation, Evidence, QueryTrace


class OutputFormatTests(unittest.TestCase):
    def test_answer_json_is_grouped_and_stable(self) -> None:
        answer = Answer(
            question="Who founded Stripe?",
            answer="Collected 1 evidence item using direct_lookup.",
            citations=[
                Citation(
                    title="Stripe",
                    url="https://stripe.com",
                    quote="Stripe was founded by Patrick and John Collison.",
                    accessed_at="2026-01-01T00:00:00+00:00",
                )
            ],
            evidence=[
                Evidence(
                    url="https://stripe.com",
                    title="Stripe",
                    quote="Stripe was founded by Patrick and John Collison.",
                    summary="Founders page summary.",
                    score=4.5,
                )
            ],
            strategy="direct_lookup",
            metadata={"documents_considered": 1},
            trace=AnswerTrace(
                queries=[QueryTrace(query="Who founded Stripe?", result_count=1, urls=["https://stripe.com"])],
                pages_fetched=1,
                pages_extracted=1,
                failures=[],
            ),
        )

        payload = format_answer_json(answer)

        self.assertEqual(payload["kind"], "answer")
        self.assertEqual(payload["request"]["question"], "Who founded Stripe?")
        self.assertEqual(payload["result"]["evidence_count"], 1)
        self.assertEqual(payload["sources"][0]["rank"], 1)
        self.assertEqual(payload["trace"]["summary"]["pages_fetched"], 1)

    def test_price_text_output_has_sections(self) -> None:
        result = PriceConsensusResult(
            question="MacBook Air M3 price",
            verdict="supported",
            summary="Consensus price: USD 1,299.00 based on 3 independent source(s).",
            confidence=1.0,
            consensus_amount=1299.0,
            consensus_currency="USD",
            agreeing=[
                PriceEvidence(
                    amount=1299.0,
                    currency="USD",
                    source_title="Store A",
                    source_url="https://a.example.com",
                    domain="a.example.com",
                    snippet="Current price $1,299.",
                    score=4.0,
                )
            ],
        )

        text = format_price_result_text(
            question="MacBook Air M3 price",
            result=result,
            trace=AnswerTrace(),
            min_sources=3,
        )
        payload = format_price_result_json(
            question="MacBook Air M3 price",
            result=result,
            trace=AnswerTrace(),
            min_sources=3,
        )

        self.assertIn("VERDICT", text)
        self.assertIn("AGREEING SOURCES", text)
        self.assertEqual(payload["kind"], "price_consensus")
        self.assertEqual(payload["result"]["consensus"]["amount"], 1299.0)
        self.assertEqual(payload["request"]["min_sources"], 3)
        self.assertIn("TRACE", format_answer_text(
            Answer(
                question="Q",
                answer="Summary",
                citations=[],
                evidence=[],
                strategy="direct_lookup",
                trace=AnswerTrace(),
            )
        ))


if __name__ == "__main__":
    unittest.main()
