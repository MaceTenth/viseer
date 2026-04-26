# Viseer Benchmark Results (2026-04-16)

This is the first lightweight benchmark pass for Viseer.
It uses automatic checks over a small set of real-world tasks and should be read as a trust and behavior snapshot, not a leaderboard claim.

## Run Summary

- Tasks: 8
- Pass: 3
- Mixed: 5
- Fail: 0
- Average automatic score: 0.78
- Median latency: 7932 ms
- SearXNG URL: http://localhost:8080

## By Category

| Category | Tasks | Pass | Mixed | Fail |
| --- | ---: | ---: | ---: | ---: |
| fact_verification | 1 | 0 | 1 | 0 |
| grounded_search | 1 | 0 | 1 | 0 |
| latest_info | 1 | 1 | 0 | 0 |
| messy_extraction | 2 | 1 | 1 | 0 |
| multi_source_synthesis | 1 | 0 | 1 | 0 |
| price_validation | 2 | 1 | 1 | 0 |

## Task Table

| Task | Kind | Category | Status | Score | Latency | Notes |
| --- | --- | --- | --- | ---: | ---: | --- |
| stripe_founders | answer | grounded_search | mixed | 0.67 | 11723 ms | Stable direct-lookup question with multiple reputable sources. |
| microsoft_ceo | answer | latest_info | pass | 1.00 | 12312 ms | Freshness-sensitive leadership lookup. |
| acetaminophen_anti_inflammatory | answer | fact_verification | mixed | 0.67 | 6744 ms | Simple medical fact-check that should surface clear supporting evidence. |
| openai_vs_anthropic_pricing | answer | multi_source_synthesis | mixed | 0.67 | 10546 ms | Comparison query that should ideally reach both vendor pricing pages. |
| chatgpt_team_pricing | price | price_validation | mixed | 0.75 | 9121 ms | SaaS pricing example where the current heuristic often finds partial but not fully supported consensus. |
| notion_ai_pricing | price | price_validation | pass | 1.00 | 4190 ms | Checks that Viseer avoids overstating confidence when pricing signals are messy. |
| saleor_storefront_fetch | fetch | messy_extraction | mixed | 0.50 | 1356 ms | Client-heavy storefront page used to test no-browser extraction quality. |
| spree_storefront_fetch | fetch | messy_extraction | pass | 1.00 | 2268 ms | Second storefront target to keep the extraction bucket from depending on one site. |

## Detailed Results

### stripe_founders

- Kind: answer
- Category: grounded_search
- Status: mixed
- Automatic score: 0.67
- Latency: 11723 ms
- Prompt: Who founded Stripe?
- Summary: Collected 4 evidence item(s) using direct_lookup. Top source: Stripe, Inc. - Wikipedia. [ 7 ] History [ edit ] Irish entrepreneur brothers John and Patrick Collison founded Stripe in Palo Alto, California , in 2010, [ 8 ] and serve as the company's president [ 9 ] and CEO, [ 10 ] respectively.
- Top sources: https://en.wikipedia.org/wiki/Stripe,_Inc., https://kitrum.com/blog/stripe-founders-the-story-of-collison-brothers/, https://en.wikipedia.org/wiki/Patrick_Collison
- Notes: Stable direct-lookup question with multiple reputable sources.
- Checks:
  - must_include_any: True
  - source_hint_hits: 0
  - source_hints_present: False
  - min_evidence: True
  - evidence_count: 4

### microsoft_ceo

- Kind: answer
- Category: latest_info
- Status: pass
- Automatic score: 1.00
- Latency: 12312 ms
- Prompt: Who is the current CEO of Microsoft?
- Summary: Collected 3 evidence item(s) using latest_info. Top source: Satya Nadella - Chairman and CEO at Microsoft | LinkedIn. The real question is how to empower… 7,319 523 Comments My annual letter: Thinking in decades, executing in quarters Oct 21, 2025 Below is my annual letter, published today in our Annual Report 2025: Dear shareholders, colleagues, customers
- Top sources: https://www.linkedin.com/in/satyanadella, https://news.microsoft.com/source/exec/satya-nadella/, https://www.forbes.com/profile/satya-nadella/
- Notes: Freshness-sensitive leadership lookup.
- Checks:
  - must_include_any: True
  - source_hint_hits: 1
  - source_hints_present: True
  - min_evidence: True
  - evidence_count: 3

### acetaminophen_anti_inflammatory

- Kind: answer
- Category: fact_verification
- Status: mixed
- Automatic score: 0.67
- Latency: 6744 ms
- Prompt: Is acetaminophen anti-inflammatory?
- Summary: Collected 4 evidence item(s) using verify_claim. Top source: Analgesic Effect of Acetaminophen: A Review of Known and Novel Mechanisms of Action - PMC (2020-11-30T00:00:00). PMC Copyright notice PMCID: PMC7734311 PMID: 33328986 Abstract Acetaminophen is one of the most commonly used analgesic agents for treating acute and chronic pain.
- Top sources: https://pmc.ncbi.nlm.nih.gov/articles/PMC7734311/, https://www.yalemedicine.org/news/acetaminophen-nsaids-over-the-counter-pain-relievers, https://www.tylenol.com/safety-dosing/what-is-acetaminophen
- Notes: Simple medical fact-check that should surface clear supporting evidence.
- Checks:
  - must_include_any: True
  - source_hint_hits: 0
  - source_hints_present: False
  - min_evidence: True
  - evidence_count: 4

### openai_vs_anthropic_pricing

- Kind: answer
- Category: multi_source_synthesis
- Status: mixed
- Automatic score: 0.67
- Latency: 10546 ms
- Prompt: OpenAI vs Anthropic pricing
- Summary: Collected 5 evidence item(s) using compare_entities. Top source: OpenAI vs Anthropic Cost Comparison 2025: Which LLM is Cheaper? - CostLens.dev | CostLens.dev (2026-04-16T10:51:17.694Z). Current Pricing (January 2025) OpenAI Pricing Model Input (per 1M tokens) Output (per 1M tokens) Best For GPT-4 Turbo $10.00 $30.00 Complex reasoning, code GPT-4 $60.00 Highest quality tasks GPT-3.5 Turbo $0.50 $1.50 Simple tasks, high volu
- Top sources: https://costlens.dev/blog/openai-vs-anthropic-cost-comparison, https://www.finout.io/blog/openai-vs-anthropic-api-pricing-comparison, https://www.vantage.sh/blog/anthropic-vs-openai-api-costs
- Notes: Comparison query that should ideally reach both vendor pricing pages.
- Checks:
  - must_include_all: True
  - source_hint_hits: 0
  - source_hints_present: False
  - min_evidence: True
  - evidence_count: 5

### chatgpt_team_pricing

- Kind: price
- Category: price_validation
- Status: mixed
- Automatic score: 0.75
- Latency: 9121 ms
- Prompt: ChatGPT Team pricing
- Summary: Consensus price: USD 25.00 based on 2 independent source(s).
- Top sources: https://help.openai.com/en/articles/8792828-what-is-chatgpt-team, https://team-gpt.com/blog/chatgpt-pricing
- Notes: SaaS pricing example where the current heuristic often finds partial but not fully supported consensus.
- Checks:
  - must_include_any: False
  - source_hint_hits: 1
  - source_hints_present: True
  - expected_verdict: True
  - min_evidence: True
  - evidence_count: 2
  - observed_verdict: insufficient

### notion_ai_pricing

- Kind: price
- Category: price_validation
- Status: pass
- Automatic score: 1.00
- Latency: 4190 ms
- Prompt: Notion AI pricing
- Summary: Consensus price: USD 10.00 based on 2 independent source(s).
- Top sources: https://userjot.com/blog/notion-pricing-2025-plans-ai-costs-explained, https://www.notion.com/pricing
- Notes: Checks that Viseer avoids overstating confidence when pricing signals are messy.
- Checks:
  - must_include_any: True
  - source_hint_hits: 1
  - source_hints_present: True
  - expected_verdict: True
  - min_evidence: True
  - evidence_count: 2
  - observed_verdict: insufficient

### saleor_storefront_fetch

- Kind: fetch
- Category: messy_extraction
- Status: mixed
- Automatic score: 0.50
- Latency: 1356 ms
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
- Latency: 2268 ms
- Prompt: https://demo.spreecommerce.org/us/en
- Summary: Spree Commerce Demo | Next.js Ecommerce Storefront
- Top sources: https://demo.spreecommerce.org/us/en
- Notes: Second storefront target to keep the extraction bucket from depending on one site.
- Checks:
  - must_include_any: True
  - min_chars: True
  - evidence_count: 1
  - observed_char_count: 504
