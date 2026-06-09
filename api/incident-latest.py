"""Public latest-incident endpoint for data-quality-watchtower.

Stdlib-only Vercel Python serverless function. Serves the most recent drift
scan exactly as the nightly cron committed it to ``api/_incident_latest.json``.
What you read here is the artifact the workflow produced and pushed to the
repo, so the proof is reproducible: clone the repo, run the runner for the same
date, and you get the same incident.

The endpoint never returns 5xx. If the artifact is missing (before the first
scan), it returns a schema-valid degraded incident with HTTP 200.

Shape: { system, schema_version, run_id, fixture, scenario, drift_detected,
severity, detection_reasons, gate_verdict, report_url, generated_at,
previous_run }. ``previous_run`` is null until a second scan has run.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from typing import Any

SYSTEM_SLUG = "data-quality-watchtower"
SCHEMA_VERSION = 1

_DIR = Path(__file__).parent
LATEST_FILE = _DIR / "_incident_latest.json"


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError, ValueError):
        return None


def _degraded() -> dict[str, Any]:
    return {
        "system": SYSTEM_SLUG,
        "benchmark_type": "drift",
        "schema_version": SCHEMA_VERSION,
        "status": "degraded",
        "run_id": None,
        "fixture": None,
        "scenario": None,
        "drift_detected": False,
        "severity": "none",
        "gate_verdict": "unknown",
        "detection_reasons": [],
        "findings": [],
        "report_url": None,
        "generated_at": _now_iso(),
        "previous_run": None,
    }


def _build_response() -> dict[str, Any]:
    incident = _read_json(LATEST_FILE)
    if isinstance(incident, dict) and incident.get("schema_version") == SCHEMA_VERSION:
        # Served verbatim: exactly what the cron committed. generated_at is the
        # scan time, not the request time, so it is the honest "as of" stamp.
        incident.setdefault("benchmark_type", "drift")
        incident.setdefault("previous_run", None)
        return incident
    return _degraded()


class handler(BaseHTTPRequestHandler):
    """Vercel Python serverless entrypoint."""

    def _write_common_headers(self) -> None:
        self.send_header(
            "Cache-Control", "public, max-age=30, stale-while-revalidate=60"
        )
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self) -> None:  # noqa: N802 (interface contract)
        self.send_response(204)
        self._write_common_headers()
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802 (interface contract)
        try:
            payload = _build_response()
        except Exception:  # noqa: BLE001 (last resort: contract forbids 5xx)
            payload = _degraded()

        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self._write_common_headers()
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt: str, *args: Any) -> None:  # noqa: A002, ARG002
        return  # Suppress default access log; Vercel captures stdout/stderr.
