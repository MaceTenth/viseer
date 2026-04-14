# Examples

These scripts are thin wrappers around the main package. They are useful when
you want copy-paste commands for a few common query patterns.

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
