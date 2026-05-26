# Data Quality Watchtower

> A monitoring assistant that detects schema drift, anomalies, and suspicious dataset changes before pipelines break — not after the dashboard turns red.

[**Live dashboard →**](https://data-quality-watchtower.eleventh.dev) · Stage: Prototype · Track: ML · Category: Data Tool

---

## Status: prototype-state

**This repository now ships a real local profiler, incident comparator, and drift gate.** The Python package can fingerprint CSV schemas, infer types, measure null-rate and numeric distribution drift, detect cardinality collapse, inspect saved profiles, export markdown incident reports, and fail a gate when a dataset change crosses explicit thresholds. The public dashboard now includes a prototype incident route that demonstrates the loop end to end.

For an example of what one of these projects looks like once graduated to production, see [NexusRAG](https://github.com/IgnazioDS/NexusRAG) — same operator, same engineering bar, fully shipped.

---

## What this project is

Pipelines that work yesterday do not work today, and the team finds out when the dashboard turns red — three hours after the upstream schema changed, after the wrong number already shipped to a customer report, after the model trained on contaminated rows.

Watchtower exists because the cost of "find out at dashboard time" is far higher than the cost of "watch for the change before it matters." The system monitors the boundary between producer and consumer, surfaces the drift at change-time, and emits an alert that names the failure rather than logging a metric drop.

## Architectural thesis

- **Monitor at the boundary, not the consumer.** Detect schema and distribution changes where the producer commits them, not three pipeline hops downstream where the symptom finally surfaces.
- **Unified contract over schema + values + cardinality.** A column added is a schema delta; a column whose distribution shifts is a value delta; a key whose unique-count drops is a cardinality delta. All three are first-class signals from the same engine.
- **Alerts are diagnostics, not metric drops.** "Column `revenue_usd` shifted toward zero (mean dropped 87% over 24h, prior baseline 14d)" beats "anomaly score crossed threshold." The alert names the failure.
- **Historical validation as a ledger.** Every check, every result, every drift signature is reconstructable. A regression three weeks later traces back to the day the contract changed.

## Failure modes this addresses

| Failure mode | What surfaces in production |
|---|---|
| Silent schema drift | Producing system adds, removes, or retypes a column. Downstream pipelines parse around the change until something explodes. |
| Anomaly buried in dashboard noise | A real anomaly hides in a dashboard already full of unexplained spikes. Nobody acts on the real one. |
| Suspicious-but-not-impossible value drift | A numeric column whose distribution shifts in a direction that is plausible but wrong (e.g., a billing column suddenly skewed toward zero). |
| Cardinality collapse | A foreign-key column drops from 50k unique values to 200. The join still runs. The result is wrong. |

## Positioning

- **Category claimed**: pre-pipeline-break detection for data systems whose downstream consumers are load-bearing — model training, customer reports, billing.
- **Category refused**: generic data-observability platforms, ETL monitoring tools that alert on job-failure rather than data-drift, BI quality dashboards.
- **Closest comparisons**:
  - **Great Expectations** — declarative data-validation framework. Watchtower is a runtime monitor, not an assertion library; it surfaces deltas the assertion author did not anticipate.
  - **Monte Carlo / Bigeye** — data-observability platforms Watchtower is conceptually adjacent to but is shaped for AI pipelines specifically, where the consumers are model-training jobs and inference contexts rather than BI dashboards.

---

## Working MVP

The local slice that ships in this repo today:

- Profile CSV datasets into a reusable JSON artifact
- Compute schema fingerprints, inferred types, row counts, null rates, unique counts, and numeric outlier summaries
- Compare two saved profile snapshots for added/removed columns, type changes, row-count drift, null-rate drift, suspicious numeric shifts, and cardinality collapse
- Emit a plain-English incident summary with severity classification
- Enforce a deploy gate from saved snapshots with explicit severity and drift thresholds

**Current product stack**: Python · CSV profiler · JSON profile artifacts · Next.js dashboard.

---

## What ships right now

This is what is in the repo today, audited honestly.

### 1. Showcase dashboard (`/`)

Next.js 14 App Router app at the live URL above. Six routes:

| path | what it shows |
|---|---|
| `/` | Overview — latest drift incident, Tier-A `/api/stats` counters, 30-day verdict history, audience + stack |
| `/prototype` | Real incident walkthrough — baseline vs drifted snapshot, gate verdict, CLI flow |
| `/telemetry` | Polling telemetry consumer — full metric grid, raw JSON, 30s visibility-aware polling, contract docs |
| `/capabilities` | MVP scope, problem statement, why-now, audience, stack — read from `project.json` |
| `/roadmap` | Three-phase timeline (showcase → MVP build → Tier-A graduation) |
| `/settings` | Theme + project metadata |

### 2. Public telemetry endpoints (`api/stats.py`, `api/incident-latest.py`)

Two stdlib-only Vercel Python functions. Both read repo-committed JSON artifacts the nightly scan produces, so there is no external database and no secret.

- `GET /api/stats` reports Tier-A live workload counters: `datasets_monitored`, `checks_run_24h`, `anomalies_detected_24h`, `schema_drifts_30d`, `last_check_at`, plus `uptime_pct_30d` and `last_active_at`. `mode` is `"live"` because the workload is real and persisted across cold starts, not because there is user traffic. Contract: [TELEMETRY_SCHEMA.md](https://github.com/IgnazioDS/IgnazioDS/blob/main/TELEMETRY_SCHEMA.md).
- `GET /api/incident-latest` serves the latest committed drift incident with a `previous_run` delta.

Both send the schema CORS and cache headers and never return HTTP 5xx. `uptime_pct_30d` is the count of distinct UTC dates with a committed scan in the trailing 30 days over the days since the first scan (capped at 30). It is derived from committed history and never seeded.

### 3. Python profiler + drift comparator (`src/data_quality_watchtower/`)

Argparse-based CLI with a real local workflow:

```
data-quality-watchtower summary       # name, summary, problem, users, stage, track
data-quality-watchtower capabilities  # shipped local capabilities
data-quality-watchtower roadmap       # docs/roadmap.md
data-quality-watchtower profile examples/orders.csv --output baseline.json
data-quality-watchtower profile examples/orders_drifted.csv --output new_run.json
data-quality-watchtower show baseline.json
data-quality-watchtower compare baseline.json new_run.json
data-quality-watchtower gate baseline.json new_run.json
```

The CLI reads `project.json` for shared metadata, but the core watchtower path now works end to end: CSV in, profile JSON out, then a saved-profile diff into a human-readable incident report or a failing gate.

### 4. Example datasets (`examples/`)

The repo includes a baseline `orders.csv` snapshot and a drifted `orders_drifted.csv` snapshot that intentionally exercise:

- row-count drop
- added and removed columns
- type change detection
- null-rate drift
- suspicious revenue outliers

### 5. Nightly benchmark + persistence

`.github/workflows/nightly-scan.yml` runs `python -m data_quality_watchtower.incident_runner` daily. The runner selects one of five drift scenarios by date, runs the engine, and commits `api/_incident_latest.json`, `api/_incident_history.json`, and a dated `reports/*.md` back to the repo. Vercel redeploys on the push and the endpoints serve the committed artifact. Persistence is repo-committed JSON, no external store and no secret.

The fixtures in `examples/fixtures/` are synthetic, seeded, and committed, so the benchmark reproduces in-repo (see [`examples/fixtures/README.md`](./examples/fixtures/README.md)). GitHub Actions also runs the Python tests, the dashboard type-check, and vitest on every push.

Reproduce a scan locally:

```bash
pip install -e .
python -m data_quality_watchtower.incident_runner
cat api/_incident_latest.json
```

---

## Architecture

```
┌──── current repo state (live benchmark, synthetic fixtures) ───────────────┐
│                                                                            │
│  nightly cron ─▶ incident_runner ─▶ watchtower engine                      │
│  (GitHub Actions)      │             (profile / compare / gate)            │
│                        ▼                                                    │
│              commits artifacts back ─▶ Vercel redeploys                     │
│              (api/_incident_*.json + reports/*.md)                          │
│                        │                                                    │
│                        ▼                                                    │
│   /api/stats (Tier-A)  +  /api/incident-latest   ◀── read committed JSON    │
│                        │                                                    │
│                        ▼                                                    │
│              Next.js dashboard (overview, prototype, telemetry)            │
└────────────────────────────────────────────────────────────────────────────┘
```

The watchtower engine (`watchtower.py`) does the profiling, comparison, and gating. `incident_runner.py` drives it nightly against the date-selected fixture and commits the result, which the stdlib endpoints serve. The `/prototype` route walks one baseline-vs-drifted comparison through the same engine.

---

## Quickstart

### Run the showcase dashboard

```bash
git clone https://github.com/IgnazioDS/data-quality-watchtower.git
cd data-quality-watchtower
npm install
npm run dev          # http://localhost:3000
```

### Run the Python watchtower

```bash
cd data-quality-watchtower
python -m data_quality_watchtower.cli profile examples/orders.csv --output baseline.json
python -m data_quality_watchtower.cli profile examples/orders_drifted.csv --output new_run.json
python -m data_quality_watchtower.cli show baseline.json
python -m data_quality_watchtower.cli compare baseline.json new_run.json
python -m data_quality_watchtower.cli gate baseline.json new_run.json
```

### Test + type-check

```bash
npm run lint
npm run type-check
npm test                    # vitest suite
python -m unittest discover -s tests -p 'test_*.py'
```

---

## Dashboard stack

Next.js 14 App Router · TypeScript strict · Tailwind 3 · Geist Sans + Mono · Radix UI · cmdk (⌘K) · sonner · next-themes · framer-motion · vitest + Testing Library.

### Keyboard shortcuts

| keys | action |
|---|---|
| ⌘K / Ctrl+K | Command palette |
| G then O / P / T / C / R | Overview / Prototype / Telemetry / Capabilities / Roadmap |

---

## More context

- **Operator's hub**: [eleventh.dev](https://eleventh.dev) — the public site this dashboard's telemetry feeds into
- **Reference shipped project**: [NexusRAG](https://github.com/IgnazioDS/NexusRAG) — production-grade multi-tenant RAG agent platform, same operator
- **Telemetry contract**: [TELEMETRY_SCHEMA.md](https://github.com/IgnazioDS/IgnazioDS/blob/main/TELEMETRY_SCHEMA.md) — what the Tier-B counters mean and what they don't
- **Status of this project**: a live public benchmark. The profiler, comparator, and drift gate run nightly against committed synthetic fixtures, with Tier-A telemetry persisted in-repo. The next step is running the same engine against real customer datasets with live alert routing.

---

## License

MIT — see [LICENSE](./LICENSE).
