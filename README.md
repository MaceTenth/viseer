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
