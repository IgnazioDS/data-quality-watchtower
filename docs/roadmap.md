# Roadmap

## Phase 1

- Profile tabular datasets and schemas
- Detect drift and row-level anomalies
- Generate plain-language incident summaries
- Store historical validation results
- Compare saved snapshots for schema, null-rate, and outlier drift
- Gate releases on explicit data-quality thresholds

Phase 1 ships now as a live public benchmark: the engine runs nightly against
committed synthetic fixtures and the results persist in the repo.

## Phase 2

- Run the same engine against real customer datasets.
- Move the committed-JSON validation ledger to a durable store as history deepens.
- Expose a service layer beyond the local CLI and the nightly cron.

## Phase 3

- Harden deployment story.
- Add richer validation and failure handling.
- Publish sample data and demos.
