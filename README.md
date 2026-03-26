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
