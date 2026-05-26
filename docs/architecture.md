# Architecture Notes

## Product Shape

Data Quality Watchtower now has a real local boundary: CSV profiling, saved profile artifacts, snapshot comparison, and a gateable incident summary. The interface is still intentionally small so the same core can evolve into an API, worker, or scheduled job without rework.

## Design Priorities

- Keep the product contract explicit and testable.
- Avoid framework lock-in early.
- Reserve room for persistence, telemetry, and deployment concerns.
- Treat generated output as an artifact that can be audited.

## Current Modules

- `models.py` defines the typed project metadata.
- `catalog.py` loads the shipped product spec.
- `cli.py` exposes summary, profile, show, compare, gate, capabilities, and roadmap commands.
- `watchtower.py` implements schema fingerprinting, type inference, null-rate analysis, numeric outlier summaries, cardinality drift detection, profile comparison, and gate assessment.
- `fixtures.py` defines the synthetic fixture catalog and the date-based scenario rotation.
- `incident_runner.py` drives the engine nightly against the date-selected fixture and writes the committed artifacts.
- `report.py` renders the incident artifact as a Markdown report.

## Public surface

- `api/stats.py` serves Tier-A live telemetry from the committed incident artifacts.
- `api/incident-latest.py` serves the latest committed incident with a previous-run delta.
- `.github/workflows/nightly-scan.yml` runs the scan and commits the result back. Persistence is repo-committed JSON, no external store.
