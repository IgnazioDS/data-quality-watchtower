# Data Quality Watchtower

> A monitoring assistant that detects schema drift, anomalies, and suspicious dataset changes before pipelines break — not after the dashboard turns red.

[**Live dashboard →**](https://data-quality-watchtower.eleventh.dev) · Stage: Ready to build · Track: ML · Category: Data Tool

---

## Status: showcase-state

**This repository is in showcase-state.** The watchtower itself — the schema-delta engine, the anomaly detector, the alert router, the historical validation store — is not yet in this repo. What ships now is a public dashboard, a stdlib-only telemetry endpoint, and a Python CLI scaffold that exposes the project contract. See [What ships right now](#what-ships-right-now) for the audit.

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

## Planned MVP

The system the dashboard will graduate to:

- Profile tabular datasets and schemas (columns, types, distributions, cardinality)
- Detect schema drift, value-distribution drift, and row-level anomalies
- Generate plain-language incident summaries naming the failure mode
- Store historical validation results — every check, every result, indexed for replay

**Planned product stack**: Python · DuckDB (analytic engine + ledger) · Great Expectations (assertion bridge) · Pandas (frame interop).

---

## What ships right now

This is what is in the repo today, audited honestly.

### 1. Showcase dashboard (`/`)

Next.js 14 App Router app at the live URL above. Five routes:

| path | what it shows |
|---|---|
| `/` | Overview — pitch banner, live `/api/stats` Tier-B counters, system status, audience + stack |
| `/telemetry` | Polling telemetry consumer — full metric grid, raw JSON, 30s visibility-aware polling, contract docs |
| `/capabilities` | MVP scope, problem statement, why-now, audience, stack — read from `project.json` |
| `/roadmap` | Three-phase timeline (showcase → MVP build → Tier-A graduation) |
| `/settings` | Theme + project metadata |

### 2. Telemetry endpoint (`api/stats.py`)

Stdlib-only Vercel Python serverless function. Reports honest GitHub-derived signals — commits, stars, last commit, primary language, lines of code. Never simulated workload metrics. Contract documented in [TELEMETRY_SCHEMA.md](https://github.com/IgnazioDS/IgnazioDS/blob/main/TELEMETRY_SCHEMA.md).

### 3. Python CLI scaffold (`src/data_quality_watchtower/`)

Argparse-based CLI exposing the project contract. Currently three subcommands:

```
data-quality-watchtower summary       # name, summary, problem, users, stage, track
data-quality-watchtower capabilities  # planned MVP capabilities
data-quality-watchtower roadmap       # docs/roadmap.md
```

The CLI reads `project.json` — a typed registry that drives the dashboard's `/capabilities` route and the CLI. When MVP work begins, the watchtower primitives (profiler, drift detector, alert router) layer onto this scaffold.

### 4. Deploy + telemetry pipeline

Vercel deploy with `/api/stats` cached 5 minutes, GitHub Actions for the type-check + vitest gate, build-time `_telemetry_static.json` artifact computed by `scripts/compute_telemetry_static.py`.

---

## Architecture (graduation path)

```
┌──── current repo state (showcase-tier) ────────────────────────────┐
│                                                                    │
│  Next.js dashboard ──▶  /api/stats (stdlib Python)  ──▶  GitHub   │
│  (5 routes)              cached 5 min                      API     │
│       │                                                            │
│       └─▶  reads ──▶  project.json  ◀── reads ── Python CLI       │
│                       (typed registry)                             │
└────────────────────────────────────────────────────────────────────┘

                              │  graduates to
                              ▼

┌──── planned MVP (Tier-A) ──────────────────────────────────────────┐
│                                                                    │
│  Watcher (DuckDB) ──▶ Profiler ──▶ Drift detector ──▶ Alert       │
│        │                  │             │              router      │
│        │                  │             │                │         │
│        │                  ▼             ▼                ▼         │
│        │            Schema ledger  Value-dist  Cardinality        │
│        │                            history    history             │
│        │                                                            │
│        └──▶ Validation ledger (every check, every result, indexed) │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

The current dashboard is the public-facing shell. The Python CLI is the spine the MVP watchtower will extend. `project.json` stays as the single source of truth for what the system claims to be.

---

## Quickstart

### Run the showcase dashboard

```bash
git clone https://github.com/IgnazioDS/data-quality-watchtower.git
cd data-quality-watchtower
npm install
npm run dev          # http://localhost:3000
```

### Run the Python CLI scaffold

```bash
cd data-quality-watchtower
python -m data_quality_watchtower.cli summary
python -m data_quality_watchtower.cli capabilities
python -m data_quality_watchtower.cli roadmap
```

### Test + type-check

```bash
npm run lint
npm run type-check
npm test                    # vitest suite
python -m pytest tests/     # python tests
```

---

## Dashboard stack

Next.js 14 App Router · TypeScript strict · Tailwind 3 · Geist Sans + Mono · Radix UI · cmdk (⌘K) · sonner · next-themes · framer-motion · vitest + Testing Library.

### Keyboard shortcuts

| keys | action |
|---|---|
| ⌘K / Ctrl+K | Command palette |
| G then O / T / C / R | Overview / Telemetry / Capabilities / Roadmap |

---

## More context

- **Operator's hub**: [eleventh.dev](https://eleventh.dev) — the public site this dashboard's telemetry feeds into
- **Reference shipped project**: [NexusRAG](https://github.com/IgnazioDS/NexusRAG) — production-grade multi-tenant RAG agent platform, same operator
- **Telemetry contract**: [TELEMETRY_SCHEMA.md](https://github.com/IgnazioDS/IgnazioDS/blob/main/TELEMETRY_SCHEMA.md) — what the Tier-B counters mean and what they don't
- **Status of this project**: showcase-tier. The watchtower graduates when the drift detector and alert router are live against a real dataset.

---

## License

MIT — see [LICENSE](./LICENSE).
