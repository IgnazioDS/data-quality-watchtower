# Data Quality Watchtower

> A monitoring assistant that detects schema drift, anomalies, and suspicious dataset changes before pipelines break.

[**Live dashboard →**](https://data-quality-watchtower.eleventh.dev) · Stage: Ready to build · Track: ML · Category: Data Tool

## What this is

**Problem.** Data issues usually surface downstream after dashboards, models, or reports are already wrong.

**Why now.** Data quality remains operationally important even for AI-native products.

## Built for

Data teams, analytics engineers, ML ops teams.

## What ships first

The MVP scope this project commits to:

- Profile tabular datasets and schemas
- Detect drift and row-level anomalies
- Generate plain-language incident summaries
- Store historical validation results

## Product stack

Python · DuckDB · Great Expectations · Pandas

## This repo

The repo currently ships a **showcase-tier** Next.js 14 dashboard at the live URL above plus a stdlib-only Python serverless function at `api/stats.py` that exposes Tier-B telemetry derived from GitHub (commits, stars, last commit, primary language, lines of code). The MVP application stack listed above is the system this dashboard will graduate to — it is not yet running production workload. See [TELEMETRY_SCHEMA.md](https://github.com/IgnazioDS/IgnazioDS/blob/main/TELEMETRY_SCHEMA.md) for what honest telemetry tiers mean here.

## Dashboard routes

| path | what it shows |
|---|---|
| `/` | Overview — pitch banner, live `/api/stats` Tier-B counters, system status, audience + stack |
| `/telemetry` | Polling telemetry consumer — full metric grid, raw JSON, 30s visibility-aware polling, contract docs |
| `/capabilities` | MVP scope, problem statement, why-now, audience, stack — read from `project.json` |
| `/roadmap` | Three-phase timeline (showcase → MVP build → Tier-A graduation) |
| `/settings` | Theme + project metadata |

## Local development

```bash
npm install
npm run dev          # http://localhost:3000
```

## Scripts

| command | what it does |
|---|---|
| `npm run dev` | Local dev server |
| `npm run build` | Production build |
| `npm run lint` | Next.js ESLint |
| `npm run type-check` | `tsc --noEmit` |
| `npm test` | Run the vitest suite |

## Dashboard stack

Next.js 14 App Router · TypeScript strict · Tailwind 3 · Geist Sans + Mono · Radix UI · cmdk (⌘K) · sonner · next-themes · framer-motion · vitest + Testing Library.

## Keyboard shortcuts

| keys | action |
|---|---|
| ⌘K / Ctrl+K | Command palette |
| G then O / T / C / R | Overview / Telemetry / Capabilities / Roadmap |
