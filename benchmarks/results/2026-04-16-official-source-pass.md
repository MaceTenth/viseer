# Viseer Benchmark Results (2026-04-16)

This is the first lightweight benchmark pass for Viseer.
It uses automatic checks over a small set of real-world tasks and should be read as a trust and behavior snapshot, not a leaderboard claim.

## Run Summary

- Tasks: 8
- Pass: 1
- Mixed: 1
- Fail: 6
- Average automatic score: 0.29
- Median latency: 28 ms
- SearXNG URL: http://localhost:8080

## By Category

| Category | Tasks | Pass | Mixed | Fail |
| --- | ---: | ---: | ---: | ---: |
| fact_verification | 1 | 0 | 0 | 1 |
| grounded_search | 1 | 0 | 0 | 1 |
| latest_info | 1 | 0 | 0 | 1 |
| messy_extraction | 2 | 1 | 1 | 0 |
| multi_source_synthesis | 1 | 0 | 0 | 1 |
| price_validation | 2 | 0 | 0 | 2 |

## Task Table

| Task | Kind | Category | Status | Score | Latency | Notes |
| --- | --- | --- | --- | ---: | ---: | --- |
| stripe_founders | answer | grounded_search | fail | 0.00 | 6245 ms | Stable direct-lookup question with multiple reputable sources. |
| microsoft_ceo | answer | latest_info | fail | 0.00 | 28 ms | Freshness-sensitive leadership lookup. |
| acetaminophen_anti_inflammatory | answer | fact_verification | fail | 0.00 | 29 ms | Simple medical fact-check that should surface clear supporting evidence. |
| openai_vs_anthropic_pricing | answer | multi_source_synthesis | fail | 0.33 | 21 ms | Comparison query that should ideally reach both vendor pricing pages. |
| chatgpt_team_pricing | price | price_validation | fail | 0.25 | 20 ms | SaaS pricing example where the current heuristic often finds partial but not fully supported consensus. |
| notion_ai_pricing | price | price_validation | fail | 0.25 | 27 ms | Checks that Viseer avoids overstating confidence when pricing signals are messy. |
| saleor_storefront_fetch | fetch | messy_extraction | mixed | 0.50 | 47976 ms | Client-heavy storefront page used to test no-browser extraction quality. |
| spree_storefront_fetch | fetch | messy_extraction | pass | 1.00 | 18983 ms | Second storefront target to keep the extraction bucket from depending on one site. |

## Detailed Results

### stripe_founders

- Kind: answer
- Category: grounded_search
- Status: fail
- Automatic score: 0.00
- Latency: 6245 ms
- Prompt: Who founded Stripe?
- Summary: No reliable evidence found for: Who founded Stripe?
- Top sources: -
- Notes: Stable direct-lookup question with multiple reputable sources.
- Checks:
  - must_include_any: False
  - source_hint_hits: 0
  - source_hints_present: False
  - min_evidence: False
  - evidence_count: 0

### microsoft_ceo

- Kind: answer
- Category: latest_info
- Status: fail
- Automatic score: 0.00
- Latency: 28 ms
- Prompt: Who is the current CEO of Microsoft?
- Summary: No reliable evidence found for: Who is the current CEO of Microsoft?
- Top sources: -
- Notes: Freshness-sensitive leadership lookup.
- Checks:
  - must_include_any: False
  - source_hint_hits: 0
  - source_hints_present: False
  - min_evidence: False
  - evidence_count: 0

### acetaminophen_anti_inflammatory

- Kind: answer
- Category: fact_verification
- Status: fail
- Automatic score: 0.00
- Latency: 29 ms
- Prompt: Is acetaminophen anti-inflammatory?
- Summary: No reliable evidence found for: Is acetaminophen anti-inflammatory?
- Top sources: -
- Notes: Simple medical fact-check that should surface clear supporting evidence.
- Checks:
  - must_include_any: False
  - source_hint_hits: 0
  - source_hints_present: False
  - min_evidence: False
  - evidence_count: 0

### openai_vs_anthropic_pricing

- Kind: answer
- Category: multi_source_synthesis
- Status: fail
- Automatic score: 0.33
- Latency: 21 ms
- Prompt: OpenAI vs Anthropic pricing
- Summary: No reliable evidence found for: OpenAI vs Anthropic pricing
- Top sources: -
- Notes: Comparison query that should ideally reach both vendor pricing pages.
- Checks:
  - must_include_all: True
  - source_hint_hits: 0
  - source_hints_present: False
  - min_evidence: False
  - evidence_count: 0

### chatgpt_team_pricing

- Kind: price
- Category: price_validation
- Status: fail
- Automatic score: 0.25
- Latency: 20 ms
- Prompt: ChatGPT Team pricing
- Summary: No price evidence could be extracted from the fetched pages.
- Top sources: -
- Notes: SaaS pricing example where the current heuristic often finds partial but not fully supported consensus.
- Checks:
  - must_include_any: False
  - source_hint_hits: 0
  - source_hints_present: False
  - expected_verdict: True
  - min_evidence: False
  - evidence_count: 0
  - observed_verdict: insufficient

### notion_ai_pricing

- Kind: price
- Category: price_validation
- Status: fail
- Automatic score: 0.25
- Latency: 27 ms
- Prompt: Notion AI pricing
- Summary: No price evidence could be extracted from the fetched pages.
- Top sources: -
- Notes: Checks that Viseer avoids overstating confidence when pricing signals are messy.
- Checks:
  - must_include_any: False
  - source_hint_hits: 0
  - source_hints_present: False
  - expected_verdict: True
  - min_evidence: False
  - evidence_count: 0
  - observed_verdict: insufficient

### saleor_storefront_fetch

- Kind: fetch
- Category: messy_extraction
- Status: mixed
- Automatic score: 0.50
- Latency: 47976 ms
- Prompt: https://demo.saleor.io/default-channel
- Summary: ACME Storefront, powered by Saleor & Next.js | Saleor Store
- Top sources: https://demo.saleor.io/default-channel
- Notes: Client-heavy storefront page used to test no-browser extraction quality.
- Checks:
  - must_include_any: True
  - min_chars: False
  - evidence_count: 1
  - observed_char_count: 229

### spree_storefront_fetch

- Kind: fetch
- Category: messy_extraction
- Status: pass
- Automatic score: 1.00
- Latency: 18983 ms
- Prompt: https://demo.spreecommerce.org/us/en
- Summary: Spree Commerce Demo | Next.js Ecommerce Storefront
- Top sources: https://demo.spreecommerce.org/us/en
- Notes: Second storefront target to keep the extraction bucket from depending on one site.
- Checks:
  - must_include_any: True
  - min_chars: True
  - evidence_count: 1
  - observed_char_count: 504
