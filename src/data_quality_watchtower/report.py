"""Plain-language incident report renderer. Standard library only.

Turns a run's incident dict (the artifact served by /api/incident-latest) into a
Markdown report a human can read without the dashboard. Committed in-repo under
reports/ so every run leaves an auditable artifact: a regression weeks later
traces back to the day the contract changed.

This is presentation of the incident artifact, not engine logic. The drift
detection lives in watchtower.py. No em-dashes in the prose, per brand discipline.
"""
from __future__ import annotations

from typing import Any

_VERDICT_LABEL = {"pass": "PASS", "fail": "FAIL"}


def _table(findings: list[dict[str, Any]]) -> list[str]:
    if not findings:
        return [
            "No material drift detected. The candidate matches the baseline "
            "contract within thresholds."
        ]
    lines = ["| Kind | Column | Detail |", "|---|---|---|"]
    for finding in findings:
        detail = finding.get("detail", {})
        detail_text = ", ".join(f"{k}={v}" for k, v in detail.items()) or "n/a"
        lines.append(
            f"| {finding.get('kind', '')} "
            f"| `{finding.get('column', '')}` "
            f"| {detail_text} |"
        )
    return lines


def render_incident_markdown(incident: dict[str, Any]) -> str:
    """Render one incident dict as a Markdown report string."""
    verdict = incident.get("gate_verdict", "pass")
    severity = incident.get("severity", "info")
    scenario_title = incident.get("scenario_title", incident.get("scenario", ""))
    findings = incident.get("findings", [])
    reasons = incident.get("detection_reasons", [])
    metrics = incident.get("metrics", {})

    lines: list[str] = []
    lines.append(f"# Incident report: {scenario_title}")
    lines.append("")
    lines.append(
        f"> Verdict: **{_VERDICT_LABEL.get(verdict, verdict.upper())}** "
        f"· Severity: **{severity}** · "
        f"Drift detected: **{str(incident.get('drift_detected', False)).lower()}**"
    )
    lines.append("")
    if incident.get("incident_summary"):
        lines.append(f"{incident['incident_summary']}")
        lines.append("")
    lines.append("## Run")
    lines.append("")
    lines.append(f"- System: `{incident.get('system', '')}`")
    lines.append(f"- Run id: `{incident.get('run_id', '')}`")
    lines.append(
        f"- Fixture: `{incident.get('fixture', '')}` "
        f"(baseline {incident.get('baseline_rows', 0)} rows vs current "
        f"{incident.get('current_rows', 0)} rows)"
    )
    lines.append(
        f"- Scenario: `{incident.get('scenario', '')}` "
        f"({incident.get('scenario_description', '')})"
    )
    lines.append(f"- Generated at: {incident.get('generated_at', '')}")
    lines.append(
        f"- Checks run: {metrics.get('checks_run', 0)} · "
        f"Anomalies detected: {metrics.get('anomalies_detected', 0)} · "
        f"Schema drifts: {metrics.get('schema_drift_count', 0)}"
    )
    lines.append("")
    lines.append("## What the scan found")
    lines.append("")
    lines.extend(_table(findings))
    lines.append("")
    if reasons:
        lines.append("## Why it matters")
        lines.append("")
        for reason in reasons:
            lines.append(f"- {reason}")
        lines.append("")
    lines.append("## Reproduce")
    lines.append("")
    lines.append("```bash")
    lines.append("git clone https://github.com/IgnazioDS/data-quality-watchtower.git")
    lines.append("cd data-quality-watchtower && pip install -e .")
    lines.append("python -m data_quality_watchtower.incident_runner")
    lines.append("cat api/_incident_latest.json")
    lines.append("```")
    lines.append("")
    lines.append(
        "All fixtures are synthetic, seeded, and committed in-repo. The scenario "
        "is selected by date, so this run reproduces exactly when re-run for the "
        "same day."
    )
    lines.append("")
    return "\n".join(lines)
