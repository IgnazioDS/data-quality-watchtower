"""Nightly drift-scan runner. Standard library only.

Drives the engine in watchtower.py: profiles the stable baseline plus the
date-selected drift scenario, compares them, gates the result, and writes three
committed artifacts:

  api/_incident_latest.json    the latest incident (served by /api/incident-latest)
  api/_incident_history.json   compact run history (windowed by /api/stats)
  reports/incident-<date>.md   a human-readable incident report

The nightly GitHub Actions cron runs ``python -m data_quality_watchtower.incident_runner``,
commits the changed artifacts back to the repo, and Vercel redeploys. The stdlib
endpoints read the committed files. No external persistence, no secrets.

The scenario is selected by date, so the verdict moves for real day over day and
the run is reproducible: re-running for the same date yields the same incident.
"""
from __future__ import annotations

import json
import tempfile
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from . import fixtures as fx
from .report import render_incident_markdown
from .watchtower import (
    ProfileComparison,
    assess_gate,
    compare_profiles,
    profile_dataset,
    profile_to_dict,
    save_json,
)

SYSTEM_SLUG = "data-quality-watchtower"
SCHEMA_VERSION = 1
MAX_HISTORY = 180  # roughly six months of daily runs
RECENT_RUNS = 30  # compact trend embedded in the latest artifact for the UI

_REPO_ROOT = Path(__file__).resolve().parents[2]
LATEST_PATH = _REPO_ROOT / "api" / "_incident_latest.json"
HISTORY_PATH = _REPO_ROOT / "api" / "_incident_history.json"
REPORTS_DIR = _REPO_ROOT / "reports"

_REPORT_URL_TEMPLATE = (
    "https://github.com/IgnazioDS/data-quality-watchtower"
    "/blob/main/reports/incident-{day}.md"
)

_REQUIRED_KEYS = (
    "system",
    "schema_version",
    "run_id",
    "fixture",
    "scenario",
    "drift_detected",
    "severity",
    "gate_verdict",
    "detection_reasons",
    "generated_at",
)


def _now_iso(now: datetime | None = None) -> str:
    moment = now or datetime.now(timezone.utc)
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


def _run_id(day: date, scenario_key: str) -> str:
    return f"dqw-{day.isoformat()}-{scenario_key}"


def _findings(comparison: ProfileComparison) -> list[dict[str, Any]]:
    """Flatten the engine's six drift categories into a unified findings list,
    each naming the failure in plain language."""
    findings: list[dict[str, Any]] = []
    for column in comparison.added_columns:
        findings.append({
            "kind": "schema_add",
            "column": column,
            "message": (
                f"New column `{column}` appeared that is absent from the "
                "baseline. Readers pinned to a fixed column set will ignore it "
                "or reject the row."
            ),
            "detail": {"present_in": "candidate", "absent_in": "baseline"},
        })
    for column in comparison.removed_columns:
        findings.append({
            "kind": "schema_remove",
            "column": column,
            "message": (
                f"Column `{column}` is missing from the candidate. Joins and "
                "selects that reference it will fail or null out downstream."
            ),
            "detail": {"present_in": "baseline", "absent_in": "candidate"},
        })
    for item in comparison.type_changes:
        findings.append({
            "kind": "type_change",
            "column": item["column"],
            "message": (
                f"Column `{item['column']}` changed type from "
                f"{item['baseline_type']} to {item['candidate_type']}. Numeric "
                "consumers will coerce or reject the values without warning."
            ),
            "detail": {
                "baseline_type": item["baseline_type"],
                "candidate_type": item["candidate_type"],
            },
        })
    for item in comparison.null_rate_drifts:
        findings.append({
            "kind": "null_rate_shift",
            "column": item["column"],
            "message": (
                f"Column `{item['column']}` null rate moved from "
                f"{item['baseline_null_rate']} to {item['candidate_null_rate']} "
                f"(delta {item['delta']:+}). A reliably populated column is now "
                "frequently empty."
            ),
            "detail": {
                "baseline_null_rate": item["baseline_null_rate"],
                "candidate_null_rate": item["candidate_null_rate"],
                "delta": item["delta"],
            },
        })
    for item in comparison.numeric_drifts:
        findings.append({
            "kind": "distribution_shift",
            "column": item["column"],
            "message": (
                f"Column `{item['column']}` mean moved from "
                f"{item['baseline_mean']} to {item['candidate_mean']} "
                f"(ratio {item['mean_delta_ratio']:+}). The values shifted in a "
                "plausible but unverified direction."
            ),
            "detail": {
                "baseline_mean": item["baseline_mean"],
                "candidate_mean": item["candidate_mean"],
                "mean_delta_ratio": item["mean_delta_ratio"],
            },
        })
    for item in comparison.cardinality_drifts:
        findings.append({
            "kind": "cardinality_collapse",
            "column": item["column"],
            "message": (
                f"Column `{item['column']}` distinct values collapsed from "
                f"{item['baseline_unique_count']} to "
                f"{item['candidate_unique_count']}. A high-cardinality key is now "
                "nearly constant, so joins fan out or collapse while the query "
                "still runs."
            ),
            "detail": {
                "baseline_unique_count": item["baseline_unique_count"],
                "candidate_unique_count": item["candidate_unique_count"],
            },
        })
    return findings


def _count_checks(baseline_columns: list[str], candidate_columns: list[str]) -> int:
    """Individual checks the comparator evaluates: one schema-presence check per
    column in the union of both schemas, plus null, type, numeric, and
    cardinality checks per shared column. Reports real work, not a guess."""
    base = set(baseline_columns)
    cand = set(candidate_columns)
    return len(base | cand) + 4 * len(base & cand)


def compute_previous_run(
    history: list[dict[str, Any]], current_run_id: str
) -> dict[str, Any] | None:
    """The most recent prior run with a different run id, if any."""
    for record in history:
        if record.get("run_id") != current_run_id:
            return {
                "run_id": record.get("run_id"),
                "generated_at": record.get("generated_at"),
                "scenario": record.get("scenario"),
                "severity": record.get("severity"),
                "gate_verdict": record.get("gate_verdict"),
                "drift_detected": record.get("drift_detected"),
            }
    return None


def _delta(previous: dict[str, Any] | None, current: dict[str, Any]) -> dict[str, str]:
    if previous is None:
        return {}
    return {
        field: f"{previous.get(field)} -> {current.get(field)}"
        for field in ("severity", "gate_verdict", "scenario")
    }


def build_incident(
    day: date,
    now: datetime,
    history: list[dict[str, Any]],
) -> dict[str, Any]:
    """Run the scan for ``day`` via watchtower.py and assemble the incident."""
    scenario = fx.select_scenario_for_date(day)
    baseline_profile = profile_dataset(fx.baseline_path())
    candidate_profile = profile_dataset(fx.scenario_path(scenario))

    with tempfile.TemporaryDirectory() as tmp:
        baseline_json = Path(tmp) / "baseline.json"
        candidate_json = Path(tmp) / "candidate.json"
        save_json(profile_to_dict(baseline_profile), baseline_json)
        save_json(profile_to_dict(candidate_profile), candidate_json)
        comparison = compare_profiles(baseline_json, candidate_json)

    gate = assess_gate(comparison)
    findings = _findings(comparison)
    schema_drift_count = (
        len(comparison.added_columns)
        + len(comparison.removed_columns)
        + len(comparison.type_changes)
    )
    checks_run = _count_checks(
        [c.name for c in baseline_profile.columns],
        [c.name for c in candidate_profile.columns],
    )
    reasons = [f["message"] for f in findings] or [comparison.incident_summary]

    run_id = _run_id(day, scenario.key)
    previous_run = compute_previous_run(history, run_id)

    incident: dict[str, Any] = {
        "system": SYSTEM_SLUG,
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "fixture": fx.BASELINE_NAME,
        "scenario": scenario.key,
        "scenario_title": scenario.title,
        "scenario_description": scenario.description,
        "baseline_rows": baseline_profile.row_count,
        "current_rows": candidate_profile.row_count,
        "drift_detected": comparison.incident_severity != "info" or bool(findings),
        "severity": comparison.incident_severity,
        "gate_verdict": "pass" if gate.passed else "fail",
        "detection_reasons": reasons,
        "incident_summary": comparison.incident_summary,
        "findings": findings,
        "datasets_monitored": fx.datasets_monitored(),
        "metrics": {
            "checks_run": checks_run,
            "anomalies_detected": len(findings),
            "schema_drift_count": schema_drift_count,
        },
        "report_url": _REPORT_URL_TEMPLATE.format(day=day.isoformat()),
        "generated_at": _now_iso(now),
    }
    incident["previous_run"] = (
        None
        if previous_run is None
        else {**previous_run, "delta": _delta(previous_run, incident)}
    )
    return incident


def _compact_run(record: dict[str, Any]) -> dict[str, Any]:
    """Minimal projection of a history record for the dashboard trend."""
    return {
        "date": record.get("date"),
        "severity": record.get("severity"),
        "gate_verdict": record.get("gate_verdict"),
        "drift_detected": record.get("drift_detected"),
        "anomalies_detected": record.get("anomalies_detected"),
    }


def to_history_record(incident: dict[str, Any]) -> dict[str, Any]:
    """Compact record for the windowed metrics in /api/stats."""
    metrics = incident["metrics"]
    return {
        "run_id": incident["run_id"],
        "generated_at": incident["generated_at"],
        "date": incident["generated_at"][:10],
        "scenario": incident["scenario"],
        "severity": incident["severity"],
        "gate_verdict": incident["gate_verdict"],
        "drift_detected": incident["drift_detected"],
        "checks_run": metrics["checks_run"],
        "anomalies_detected": metrics["anomalies_detected"],
        "schema_drift_count": metrics["schema_drift_count"],
        "status": "ok",
    }


def merge_history(
    history: list[dict[str, Any]], record: dict[str, Any]
) -> list[dict[str, Any]]:
    """Prepend the record newest-first, replacing any same-day rerun, trimmed."""
    kept = [r for r in history if r.get("run_id") != record["run_id"]]
    return [record, *kept][:MAX_HISTORY]


def validate_incident(incident: dict[str, Any]) -> None:
    """Fail loudly before writing anything that would break the contract."""
    missing = [key for key in _REQUIRED_KEYS if key not in incident]
    if missing:
        raise ValueError(f"Incident missing required keys: {missing}")
    if incident["schema_version"] != SCHEMA_VERSION:
        raise ValueError(
            f"schema_version must be {SCHEMA_VERSION}, "
            f"got {incident['schema_version']!r}"
        )


def run(
    day: date | None = None,
    now: datetime | None = None,
    history: list[dict[str, Any]] | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Pure entrypoint: returns (incident, new_history). Does no file IO."""
    moment = now or datetime.now(timezone.utc)
    today = day or moment.date()
    prior = list(history or [])
    incident = build_incident(today, moment, prior)
    new_history = merge_history(prior, to_history_record(incident))
    # Embed a compact trend (newest first, current run included) so the
    # dashboard can render the verdict history without another endpoint.
    incident["recent_runs"] = [_compact_run(r) for r in new_history[:RECENT_RUNS]]
    validate_incident(incident)
    return incident, new_history


def _load_history(path: Path) -> list[dict[str, Any]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError, ValueError):
        return []
    return data if isinstance(data, list) else []


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    history = _load_history(HISTORY_PATH)
    incident, new_history = run(history=history)

    report = render_incident_markdown(incident)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORTS_DIR / f"incident-{incident['generated_at'][:10]}.md"
    report_path.write_text(report, encoding="utf-8")

    _write_json(LATEST_PATH, incident)
    _write_json(HISTORY_PATH, new_history)

    print(
        f"scan complete: scenario={incident['scenario']} "
        f"verdict={incident['gate_verdict']} severity={incident['severity']} "
        f"checks={incident['metrics']['checks_run']} "
        f"history={len(new_history)} runs"
    )
    print(f"  wrote {LATEST_PATH.relative_to(_REPO_ROOT)}")
    print(f"  wrote {HISTORY_PATH.relative_to(_REPO_ROOT)}")
    print(f"  wrote {report_path.relative_to(_REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
