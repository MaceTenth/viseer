from __future__ import annotations

import unittest

from websearch_agents.fetch.trafilatura_extractor import TrafilaturaExtractor


class StubFetcher:
    def __init__(self, pages: dict[str, str]):
        self.pages = pages

    def fetch(self, url: str) -> str:
        return self.pages[url]


class StructuredRecoveryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.extractor = TrafilaturaExtractor(weak_text_threshold=400, max_json_fetches=2)

    def test_recovers_json_ld_article_text(self) -> None:
        html = """
        <html>
          <head>
            <title>Example Article</title>
            <script type="application/ld+json">
              {"headline":"Example headline","articleBody":"This article explains why Stripe was founded in 2010."}
            </script>
          </head>
          <body><div id="root"></div></body>
        </html>
        """

        document = self.extractor.extract("https://example.com/article", html)

        self.assertIsNotNone(document)
        self.assertIn("json_ld", document.metadata["structured_sources"])
        self.assertIn("Example headline", document.text)

    def test_recovers_next_data_payload(self) -> None:
        html = """
        <html>
          <head>
            <title>Hydrated Page</title>
            <script id="__NEXT_DATA__" type="application/json">
              {"props":{"pageProps":{"title":"Hydrated title","content":"Hydrated content about the Microsoft CEO."}}}
            </script>
          </head>
          <body><div id="__next"></div></body>
        </html>
        """

        document = self.extractor.extract("https://example.com/hydrated", html)

        self.assertEqual(document.extraction_method, "hydration")
        self.assertIn("Hydrated content", document.text)
        self.assertIn("next_root", document.metadata["dynamic_signals"])

    def test_recovers_same_origin_api_json(self) -> None:
        html = """
        <html>
          <head><title>Products</title></head>
          <body>
            <script>window.__DATA__ = "/api/product.json";</script>
          </body>
        </html>
        """
        fetcher = StubFetcher(
            {
                "https://example.com/api/product.json": '{"name":"MacBook Air","price":"1299 USD","summary":"Current listed price."}'
            }
        )

        document = self.extractor.extract("https://example.com/products", html, fetcher=fetcher)

        self.assertEqual(document.extraction_method, "api_json")
        self.assertIn("api_json", document.metadata["structured_sources"])
        self.assertIn("MacBook Air", document.text)

    def test_marks_unsupported_dynamic_page_honestly(self) -> None:
        html = """
        <html>
          <head>
            <title>Client App</title>
            <script src="/static/app.js"></script>
            <script>fetch("/api/bootstrap")</script>
            <script>window.__APP__ = true;</script>
            <script>console.log("boot")</script>
            <script>console.log("ready")</script>
          </head>
          <body><div id="root"></div></body>
        </html>
        """

        document = self.extractor.extract("https://example.com/app", html)

        self.assertIsNotNone(document)
        self.assertTrue(document.metadata["recovery_failed"])
        self.assertIn("script_heavy", document.metadata["dynamic_signals"])
        self.assertEqual(document.text, "Client App")

    def test_static_html_keeps_existing_behavior(self) -> None:
        html = """
        <html>
          <head><title>Plain Page</title></head>
          <body><p>Plain article text with enough words to exceed the weak threshold. </p></body>
        </html>
        """ + ("Meaningful text. " * 40)

        document = self.extractor.extract("https://example.com/plain", html)

        self.assertIsNotNone(document)
        self.assertIn(document.extraction_method, {"fallback", "trafilatura"})
        self.assertEqual(document.metadata["structured_sources"], [])
        self.assertFalse(document.metadata["recovery_failed"])


if __name__ == "__main__":
    unittest.main()
