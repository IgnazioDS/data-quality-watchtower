# Data Quality Watchtower

A monitoring assistant that detects schema drift, anomalies, and suspicious dataset changes before pipelines break.

## Problem

Data issues usually surface downstream after dashboards, models, or reports are already wrong.

## Users

Data teams, analytics engineers, ML ops teams

## Core Capabilities

- Profile tabular datasets and schemas
- Detect drift and row-level anomalies
- Generate plain-language incident summaries
- Store historical validation results

## Why This Matters

Data quality remains operationally important even for AI-native products.

## Architecture

- `core`: domain logic for data quality watchtower.
- `cli`: operator-facing entrypoint for local workflows and smoke checks.
- `docs/`: product notes, roadmap, and architecture decisions.
- `tests/`: baseline regression coverage for the project contract.

## Local Usage

```bash
uv run data-quality-watchtower summary
uv run data-quality-watchtower capabilities
uv run data-quality-watchtower roadmap
```

## Initial Stack Direction

Python, DuckDB, Great Expectations, Pandas

## Delivery Standard

- Clear product thesis
- Setup that works locally
- Tests for the primary contract
- Documentation for roadmap and architecture
- Space for production integrations in the next iteration

## Showcase

This repository ships with a static Vercel-ready landing page for demos and previews.

```bash
vercel deploy -y
```

The deployed site presents Data Quality Watchtower as a standalone product page.

## Production telemetry

This deployment exposes public, aggregate metrics at `/api/stats`. The endpoint
is consumed by the Production Telemetry panel on https://eleventh.dev. The
schema is documented at
https://github.com/IgnazioDS/IgnazioDS/blob/main/TELEMETRY_SCHEMA.md.

This system is in **showcase mode** — the Vercel deploy is a public landing
page, not a system processing production workload. The endpoint exposes real
GitHub-derived metrics about the codebase rather than fabricated activity
counters. Tier-A workload metrics (`checks_run_24h`, `anomalies_detected_24h`,
`schema_drifts_30d`, etc.) are added when the system is promoted from showcase
to production.

Sample response:

```bash
$ curl -i https://data-quality-watchtower.vercel.app/api/stats
HTTP/1.1 200 OK
Content-Type: application/json
Cache-Control: public, max-age=30, stale-while-revalidate=60
Access-Control-Allow-Origin: *

{
  "system": "data-quality-watchtower",
  "mode": "showcase",
  "status": "operational",
  "last_deployed_at": "2026-04-27T18:43:06Z",
  "last_commit_at": "2026-03-26T14:33:15Z",
  "metrics": {
    "commits_30d": 0,
    "commits_total": 2,
    "primary_language": "HTML",
    "repo_stars": 0,
    "lines_of_code": 1177
  },
  "schema_version": 1,
  "generated_at": "2026-04-27T18:43:08Z"
}
```

The endpoint never returns HTTP 5xx. If GitHub is unreachable, the response
status flips to `"degraded"` and metric values fall back to last known good
(or zero) values, while the JSON contract remains valid.

To regenerate `lines_of_code` before deploying:

```bash
python3 scripts/compute_telemetry_static.py
git add api/_telemetry_static.json
```
