from __future__ import annotations

import unittest

from benchmarks.runner import BenchmarkTask, build_markdown_report, evaluate_task_checks, summarize_results


class BenchmarkRunnerTests(unittest.TestCase):
    def test_evaluate_answer_checks(self) -> None:
        task = BenchmarkTask(
            id="stripe_founders",
            kind="answer",
            category="grounded_search",
            question="Who founded Stripe?",
            strategy="direct",
            must_include_any=["Patrick Collison"],
            expected_source_hints=["stripe.com"],
            min_evidence=1,
        )
        payload = {
            "result": {"summary": "Patrick Collison co-founded Stripe."},
            "sources": [
                {
                    "title": "Stripe",
                    "quote": "Patrick Collison is a co-founder.",
                    "summary": "Founders.",
                    "url": "https://stripe.com/about",
                }
            ],
        }

        checks = evaluate_task_checks(task, payload)

        self.assertEqual(checks["automatic_status"], "pass")
        self.assertTrue(checks["must_include_any"])
        self.assertTrue(checks["source_hints_present"])
        self.assertTrue(checks["min_evidence"])

    def test_evaluate_fetch_checks(self) -> None:
        task = BenchmarkTask(
            id="saleor_fetch",
            kind="fetch",
            category="messy_extraction",
            url="https://demo.saleor.io/default-channel",
            must_include_any=["Saleor"],
            min_chars=500,
        )
        payload = {
            "result": {
                "title": "Saleor Store",
                "url": "https://demo.saleor.io/default-channel",
                "text": "Saleor demo storefront",
                "char_count": 800,
            }
        }

        checks = evaluate_task_checks(task, payload)

        self.assertEqual(checks["automatic_status"], "pass")
        self.assertTrue(checks["must_include_any"])
        self.assertTrue(checks["min_chars"])

    def test_summarize_and_markdown(self) -> None:
        results = [
            {
                "id": "a",
                "kind": "answer",
                "category": "grounded_search",
                "latency_ms": 1200,
                "notes": "A note",
                "question": "Question",
                "url": None,
                "observed_summary": "Summary",
                "top_source_urls": ["https://example.com"],
                "checks": {"automatic_status": "pass", "automatic_score": 1.0},
            },
            {
                "id": "b",
                "kind": "price",
                "category": "price_validation",
                "latency_ms": 2200,
                "notes": "",
                "question": "Price question",
                "url": None,
                "observed_summary": "Summary",
                "top_source_urls": ["https://example.org"],
                "checks": {"automatic_status": "mixed", "automatic_score": 0.5},
            },
        ]

        summary = summarize_results(results)
        report = build_markdown_report(
            {
                "run": {
                    "started_at": "2026-04-16T12:00:00+00:00",
                    "finished_at": "2026-04-16T12:05:00+00:00",
                    "task_count": 2,
                    "searxng_url": "http://localhost:8080",
                },
                "summary": summary,
                "tasks": results,
            }
        )

        self.assertEqual(summary["pass_count"], 1)
        self.assertEqual(summary["mixed_count"], 1)
        self.assertIn("# Viseer Benchmark Results (2026-04-16)", report)
        self.assertIn("| grounded_search | 1 | 1 | 0 | 0 |", report)


if __name__ == "__main__":
    unittest.main()
