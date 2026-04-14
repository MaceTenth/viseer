# Viseer

Viseer: grounded search and validation for AI agents.

It helps agents:
- search the web with SearXNG
- fetch pages with the standard library
- extract clean content with an optional `trafilatura` fast path
- rank evidence with lightweight heuristics
- validate claims or prices from multiple sources
- return traceable answers with citations and a small execution trace

## Why this exists

Web search is one of the hardest agent tools to use well.
This repo focuses on the part that matters: querying, evidence collection,
ranking, and citation output.

## What v1 includes

- Provider interface plus SearXNG and mock providers
- HTTP fetcher
- `trafilatura` extractor with a built-in fallback extractor
- Deterministic strategies for direct lookup, latest info, verification, comparisons, and pricing
- Lightweight evidence ranking with URL dedupe, domain trust, and optional recency boosts
- A price-consensus example that checks whether several sources agree
- CLI output in text or JSON
- Small unit test suite with no network calls

## Install

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

If you want better HTML extraction:

```bash
pip install -e .[extract]
```

If you want richer terminal output:

```bash
pip install -e '.[ui]'
```

Or both:

```bash
pip install -e '.[extract,ui]'
```

## Local SearXNG

If you do not already have a SearXNG instance, this repo now includes a small
local setup, and the CLI defaults to `http://localhost:8080`.

Start it:

```bash
docker compose up -d
```

Check it:

```bash
curl "http://localhost:8080/search?q=openai&format=json"
```

Then run the toolkit against that local URL:

```bash
viseer \
  "Who is the current CEO of Microsoft?" \
  --strategy latest
```

Stop it:

```bash
docker compose down
```

## Run

With the bundled Docker setup running, this is the shortest path:

```bash
viseer \
  "Who is the current CEO of Anthropic?" \
  --strategy latest
```

JSON output:

```bash
viseer \
  "Is acetaminophen anti-inflammatory?" \
  --strategy verify \
  --json
```

Rich terminal output:

```bash
viseer \
  "Who founded Stripe?" \
  --strategy direct
```

Rich-highlighted JSON:

```bash
viseer \
  "Who founded Stripe?" \
  --strategy direct \
  --json \
  --rich
```

Disable Rich output:

```bash
viseer \
  "Who founded Stripe?" \
  --strategy direct \
  --plain
```

Use `--searxng-url` only if you want a non-default SearXNG instance:

```bash
viseer \
  "Who founded Stripe?" \
  --strategy direct \
  --searxng-url https://your-searxng.example.com
```

Price validation example:

```bash
python examples/price_check.py "MacBook M4 price"
```

## Sample Output

These examples were generated on April 14, 2026 with the bundled local
SearXNG stack. Output is abridged for readability, and the exact sources,
scores, and snippets will change over time.

Direct lookup:

```bash
viseer "Who founded Stripe?" --strategy direct --plain
```

```text
QUESTION
Who founded Stripe?

STRATEGY
Direct Lookup

SUMMARY
Collected 4 evidence item(s) using direct_lookup. Top source: Stripe co-founder
and CEO Patrick Collison on "prizing the small details" - Haas News | UC
Berkeley Haas (2024-04-30T16:49:40+00:00).

TOP SOURCES
[1] Stripe co-founder and CEO Patrick Collison on "prizing the small details" - Haas News | UC Berkeley Haas
    Score: 4.50
    Published: 2024-04-30T16:49:40+00:00
[2] Stripe, Inc. - Wikipedia
    Score: 3.00

TRACE
Queries: 1
Pages fetched: 4
Pages extracted: 4
Failures: 1
```

Claim validation:

```bash
viseer "Is acetaminophen anti-inflammatory?" --strategy verify --plain
```

```text
QUESTION
Is acetaminophen anti-inflammatory?

STRATEGY
Verify Claim

SUMMARY
Collected 4 evidence item(s) using verify_claim. Top source:
NSAIDs vs. Acetaminophen: Which Over-the-Counter Medicine Should I Use?
| Yale Medicine (2023-03-17T00:00:00).

TOP SOURCES
[1] Yale Medicine
    Score: 4.00
[2] Healthline
    Score: 4.00
[3] TYLENOL®
    Score: 4.00

TRACE
Queries: 1
Pages fetched: 4
Pages extracted: 4
Failures: 1
```

Price validation:

```bash
python examples/price_check.py "ChatGPT Team pricing" --plain
```

```text
QUESTION
ChatGPT Team pricing

VERDICT
mixed (confidence=0.20)

SUMMARY
Consensus price: USD 30.00 based on 1 independent source(s). 1 source(s)
disagreed or showed another price.

RULE
Supported requires at least 3 independent source(s).

AGREEING SOURCES
[1] Content Whale
    Price: USD 30.00

CONFLICTING SOURCES
[1] IntuitionLabs
    Price: USD 20.00

TRACE
Queries: 1
Pages fetched: 4
Pages extracted: 4
Failures: 1
```

## Examples

The [`examples/`](/README.md) folder has
small wrappers for common patterns:

```bash
python examples/company_lookup.py
python examples/latest_news.py
python examples/fact_check.py
python examples/compare_tools.py
python examples/price_check.py
```

## Design principles

- Keep the core small
- Prefer deterministic steps over long agent loops
- Separate provider, fetch, extraction, ranking, and synthesis
- Make every answer traceable to evidence
- Ship optional components as optional components

## Project shape

The code intentionally stays flatter than the original larger tree so the repo
is easier to read in one sitting. If people use it, the next expansion points
should be evals, richer recency handling, and optional browser fallback.

## Tests

```bash
python3 -m unittest discover -s tests
```
