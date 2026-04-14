from __future__ import annotations

from .config import PipelineConfig
from .fetch.http_fetcher import HttpFetcher
from .fetch.trafilatura_extractor import TrafilaturaExtractor
from .ranking import dedupe_search_results, normalize_url, rank_documents
from .synthesis import build_citations, render_answer
from .types import Answer, AnswerTrace, QueryTrace


class SearchPipeline:
    def __init__(
        self,
        provider,
        strategy,
        config: PipelineConfig | None = None,
        fetcher: HttpFetcher | None = None,
        extractor: TrafilaturaExtractor | None = None,
        browser_fallback=None,
    ):
        self.provider = provider
        self.strategy = strategy
        self.config = config or PipelineConfig()
        self.fetcher = fetcher or HttpFetcher(
            timeout=self.config.request_timeout,
            user_agent=self.config.user_agent,
        )
        self.extractor = extractor or TrafilaturaExtractor()
        self.browser_fallback = browser_fallback

    def collect_documents(self, question: str, limit_per_query: int | None = None):
        per_query_limit = limit_per_query or self.config.search_limit
        queries = self.strategy.build_queries(question)

        docs = []
        failures: list[dict[str, str]] = []
        query_traces: list[QueryTrace] = []
        fetched_count = 0
        extracted_count = 0
        seen_urls: set[str] = set()

        for query in queries:
            query_results = dedupe_search_results(self.provider.search(query, limit=per_query_limit))
            query_traces.append(
                QueryTrace(
                    query=query,
                    result_count=len(query_results),
                    urls=[result.url for result in query_results],
                )
            )

            for result in query_results:
                normalized = normalize_url(result.url)
                if normalized in seen_urls:
                    continue
                seen_urls.add(normalized)

                try:
                    html = self.fetcher.fetch(result.url)
                    fetched_count += 1
                    doc = self.extractor.extract(result.url, html)
                    if doc is None and self.browser_fallback is not None:
                        doc = self.browser_fallback.fetch_and_extract(result.url)
                    if doc is None:
                        failures.append({"url": result.url, "error": "extraction returned no text"})
                        continue

                    doc.title = doc.title or result.title or result.url
                    doc.published_at = doc.published_at or result.published_at
                    doc.metadata["source"] = result.source
                    doc.metadata["search_snippet"] = result.snippet
                    docs.append(doc)
                    extracted_count += 1
                except Exception as exc:  # pragma: no cover - exercised via tests with fake exceptions
                    failures.append({"url": result.url, "error": str(exc)})

            ranked = rank_documents(question, docs, recency_weight=self.strategy.recency_weight)
            enough_evidence = [item for item in ranked if item.score > 0]
            if self.strategy.should_stop(len(enough_evidence)):
                break

        trace = AnswerTrace(
            queries=query_traces,
            pages_fetched=fetched_count,
            pages_extracted=extracted_count,
            failures=failures,
        )
        return docs, trace

    def run(self, question: str, limit_per_query: int | None = None) -> Answer:
        docs, trace = self.collect_documents(question, limit_per_query=limit_per_query)
        ranked = rank_documents(question, docs, recency_weight=self.strategy.recency_weight)
        evidence = [item for item in ranked if item.score > 0][: self.config.max_evidence]
        if not evidence:
            evidence = ranked[: self.config.max_evidence]

        return Answer(
            question=question,
            answer=render_answer(question, evidence, self.strategy.name),
            citations=build_citations(evidence),
            evidence=evidence,
            strategy=self.strategy.name,
            metadata={"documents_considered": len(docs)},
            trace=trace,
        )
