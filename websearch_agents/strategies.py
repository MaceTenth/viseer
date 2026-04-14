from __future__ import annotations


class SearchStrategy:
    name = "direct_lookup"
    recency_weight = 0.0

    def build_queries(self, question: str) -> list[str]:
        return [question]

    def should_stop(self, evidence_count: int) -> bool:
        return evidence_count >= 3


class DirectLookupStrategy(SearchStrategy):
    """
    Use when the question is likely to have one stable answer.
    Examples:
    - Who founded Stripe?
    - What is the capital of Japan?
    Avoid when:
    - the query is time-sensitive
    - multiple conflicting sources are expected
    """

    name = "direct_lookup"

    def build_queries(self, question: str) -> list[str]:
        return [question]


class LatestInfoStrategy(SearchStrategy):
    """
    Use when the question is time-sensitive and freshness matters.
    Examples:
    - Who is the current CEO of Microsoft?
    - What is the latest CPI reading?
    Avoid when:
    - the answer is historical and stable
    - older primary sources are better than fresh summaries
    """

    name = "latest_info"
    recency_weight = 1.0

    def build_queries(self, question: str) -> list[str]:
        return [
            question,
            f"{question} latest",
            f"{question} official",
            f"{question} today",
        ]

    def should_stop(self, evidence_count: int) -> bool:
        return evidence_count >= 4


class VerifyClaimStrategy(SearchStrategy):
    """
    Use when the user gives a claim that may be true, false, or misleading.
    Examples:
    - Did company X announce layoffs this week?
    - Is it true that product Y was discontinued?
    Avoid when:
    - the task is open-ended research
    - the question is better served by a direct factual lookup
    """

    name = "verify_claim"
    recency_weight = 0.25

    def build_queries(self, question: str) -> list[str]:
        return [
            question,
            f"\"{question}\"",
            f"{question} fact check",
            f"{question} official statement",
        ]


class CompareEntitiesStrategy(SearchStrategy):
    """
    Use when the user wants to compare two products, companies, or tools.
    Examples:
    - Compare Bun vs Node.js for build tooling
    - OpenAI vs Anthropic pricing comparison
    Avoid when:
    - only one entity is being researched
    - the task requires a definitive single-source answer
    """

    name = "compare_entities"
    recency_weight = 0.5

    def build_queries(self, question: str) -> list[str]:
        return [
            question,
            f"{question} comparison",
            f"{question} official docs",
        ]

    def should_stop(self, evidence_count: int) -> bool:
        return evidence_count >= 5


class PriceValidationStrategy(SearchStrategy):
    """
    Use when the user wants to validate a product or service price.
    Examples:
    - MacBook Air M3 price
    - ChatGPT Team pricing
    Avoid when:
    - the target is ambiguous across regions or variants
    - there is no stable public price page to compare
    """

    name = "price_validation"
    recency_weight = 0.5

    def build_queries(self, question: str) -> list[str]:
        return [
            question,
            f"{question} price",
            f"{question} official price",
            f"{question} buy",
            f"{question} MSRP",
        ]

    def should_stop(self, evidence_count: int) -> bool:
        return evidence_count >= 4


STRATEGY_ALIASES = {
    "direct": DirectLookupStrategy,
    "direct_lookup": DirectLookupStrategy,
    "latest": LatestInfoStrategy,
    "latest_info": LatestInfoStrategy,
    "verify": VerifyClaimStrategy,
    "verify_claim": VerifyClaimStrategy,
    "compare": CompareEntitiesStrategy,
    "compare_entities": CompareEntitiesStrategy,
    "price": PriceValidationStrategy,
    "price_validation": PriceValidationStrategy,
}


def resolve_strategy(name: str | None) -> SearchStrategy:
    strategy_cls = STRATEGY_ALIASES.get((name or "direct").strip().lower())
    if strategy_cls is None:
        valid = ", ".join(sorted(STRATEGY_ALIASES))
        raise ValueError(f"Unknown strategy '{name}'. Valid options: {valid}")
    return strategy_cls()
