# Examples

These scripts are thin wrappers around the main package. They are useful when
you want copy-paste commands for a few common query patterns.

They are optional. The main installed commands are:

- `viseer` for search and validation
- `viseer-fetch` for direct page extraction

Use the example scripts when you want:

- demo queries
- multi-step workflows
- shortcuts while developing locally

Before running the examples, start the bundled local SearXNG:

```bash
docker compose up -d
```

The scripts default to `http://localhost:8080`, so no extra flag is needed.
If you want a different instance, you can either export `SEARXNG_URL` once:

```bash
export SEARXNG_URL=http://localhost:8080
```

Or pass it per command:

```bash
python examples/company_lookup.py --searxng-url http://localhost:8080
```

If you want colorful terminal output, install:

```bash
pip install -e '.[ui]'
```

## Available scripts

Direct lookup:

```bash
python examples/company_lookup.py
python examples/company_lookup.py "Who is the CEO of Nvidia?"
python examples/company_lookup.py "Who is the CEO of Nvidia?" --plain
```

Latest info:

```bash
python examples/latest_news.py
python examples/latest_news.py "What is the latest CPI reading in the United States?"
```

Reddit/community search:

```bash
python examples/company_lookup.py "Framework laptop long term experience" --provider reddit --strategy reddit
python examples/company_lookup.py "best debugging tools" --provider reddit --strategy reddit --subreddit Python --reddit-sort top --reddit-time year
```

Claim verification:

```bash
python examples/fact_check.py
python examples/fact_check.py "Did the FDA approve a new obesity drug this month?"
```

Comparison:

```bash
python examples/compare_tools.py
python examples/compare_tools.py "OpenAI vs Anthropic pricing"
```

Search then fetch one chosen source:

```bash
python examples/search_then_fetch.py
python examples/search_then_fetch.py "Who founded Stripe?" --source-rank 2 --plain
python examples/search_then_fetch.py "Who founded Stripe?" --source-rank 2 --json
python examples/search_then_fetch.py "Who is the current CEO of Microsoft?" --strategy latest
```

Price consensus:

```bash
python examples/price_check.py
python examples/price_check.py "MacBook Air M3 13-inch price"
python examples/price_check.py "ChatGPT Team pricing" --json
python examples/price_check.py "ChatGPT Team pricing" --json --rich
```

JSON output works on every script:

```bash
python examples/fact_check.py --json
```
