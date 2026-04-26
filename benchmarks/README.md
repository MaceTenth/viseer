# Benchmarks

Viseer includes a small, reproducible benchmark set aimed at trust signals
rather than leaderboard chasing.

The first benchmark set is intentionally small:

- grounded search
- latest info
- fact verification
- multi-source synthesis
- price validation
- messy extraction pages

The tasks live in [`benchmarks/tasks.json`](./tasks.json).

## Run

Start the bundled SearXNG instance first:

```bash
docker compose up -d
```

Then run the benchmark from the repo root:

```bash
python -m benchmarks.runner \
  --tasks benchmarks/tasks.json \
  --output benchmarks/results/local-run.json \
  --markdown benchmarks/results/local-run.md
```

## What gets measured

This first version focuses on lightweight, reproducible checks:

- latency
- whether extraction produced usable text
- whether evidence or sources were found
- whether the output contains expected key terms
- whether source URLs match expected domain hints
- whether price-validation tasks returned the expected verdict shape

These are automatic checks, not academic truth labels. They are meant to show
whether Viseer is behaving plausibly and transparently on a small but varied set
of real-world tasks.

## Published results

The first published run lives in:

- [`benchmarks/results/2026-04-16-initial.md`](./results/2026-04-16-initial.md)
- [`benchmarks/results/2026-04-16-initial.json`](./results/2026-04-16-initial.json)
