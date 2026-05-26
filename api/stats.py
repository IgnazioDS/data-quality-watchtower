"""Public Tier-A telemetry endpoint for data-quality-watchtower.

Stdlib-only Vercel Python serverless function. Reports the real, recurring
drift-scan workload: the nightly GitHub Actions cron runs the scan, commits the
result JSON back to the repo, Vercel redeploys, and this function reads the
committed artifacts. There is no external database, no secret, and no in-memory
counter that resets on cold start. ``mode`` is ``"live"`` because the workload
is real and persisted durably in the repo.

Metrics describe THAT workload truthfully and nothing else. No user-traffic
counters are fabricated; the fixtures are synthetic and labelled as such.

Contract: https://github.com/IgnazioDS/IgnazioDS/blob/main/TELEMETRY_SCHEMA.md
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from typing import Any

SYSTEM_SLUG = "data-quality-watchtower"
SCHEMA_VERSION = 1
MODE = "live"

_DAY_SECONDS = 86_400
WINDOW_24H = _DAY_SECONDS
WINDOW_30D = 30 * _DAY_SECONDS
_SKEW_TOLERANCE_S = 120  # tolerate minor clock skew between cron and request

# Sanity caps per TELEMETRY_SCHEMA.md. A counter that exceeds its cap is
# clamped rather than exposed.
SAFETY_CAPS: dict[str, int] = {
    "datasets_monitored": 1_000_000,
    "checks_run_24h": 1_000_000,
    "anomalies_detected_24h": 1_000_000,
    "schema_drifts_30d": 1_000_000,
}

_DIR = Path(__file__).parent
LATEST_FILE = _DIR / "_incident_latest.json"
HISTORY_FILE = _DIR / "_incident_history.json"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _now_iso() -> str:
    return _now().strftime("%Y-%m-%dT%H:%M:%SZ")


def _cap(name: str, value: int) -> int:
    cap = SAFETY_CAPS.get(name)
    return min(value, cap) if cap is not None else value


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError, ValueError):
        return None


def _parse_ts(iso: str | None) -> datetime | None:
    if not iso:
        return None
    try:
        return datetime.strptime(iso, "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=timezone.utc
        )
    except (ValueError, TypeError):
        return None


def _within(ts: datetime | None, now: datetime, window: int) -> bool:
    if ts is None:
        return False
    delta = (now - ts).total_seconds()
    return -_SKEW_TOLERANCE_S <= delta <= window


def _int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _metrics(
    latest: dict[str, Any] | None,
    history: list[dict[str, Any]],
    now: datetime,
) -> dict[str, Any]:
    datasets = _int(latest.get("datasets_monitored")) if isinstance(latest, dict) else 0
    last_check_at = latest.get("generated_at") if isinstance(latest, dict) else None

    checks_24h = anomalies_24h = schema_30d = 0
    for record in history:
        ts = _parse_ts(record.get("generated_at"))
        if _within(ts, now, WINDOW_24H):
            checks_24h += _int(record.get("checks_run"))
            anomalies_24h += _int(record.get("anomalies_detected"))
        if _within(ts, now, WINDOW_30D):
            schema_30d += _int(record.get("schema_drift_count"))

    return {
        "datasets_monitored": _cap("datasets_monitored", datasets),
        "checks_run_24h": _cap("checks_run_24h", checks_24h),
        "anomalies_detected_24h": _cap("anomalies_detected_24h", anomalies_24h),
        "schema_drifts_30d": _cap("schema_drifts_30d", schema_30d),
        "last_check_at": last_check_at,
    }


def _uptime_pct_30d(history: list[dict[str, Any]], now: datetime) -> float:
    """Share of expected daily scans that actually ran in the trailing 30 days.

    Honest cadence-reliability measure: the count of distinct UTC dates with a
    committed scan, over the number of days the watchtower has been running
    (capped at 30). Derived entirely from committed run history, never seeded.
    The method is documented in the repo README.
    """
    dates_in_window: set[Any] = set()
    first_ts: datetime | None = None
    for record in history:
        ts = _parse_ts(record.get("generated_at"))
        if ts is None:
            continue
        if first_ts is None or ts < first_ts:
            first_ts = ts
        if _within(ts, now, WINDOW_30D):
            dates_in_window.add(ts.date())
    if not dates_in_window or first_ts is None:
        return 0.0
    days_since_first = (now.date() - first_ts.date()).days + 1
    expected = max(1, min(30, days_since_first))
    pct = 100.0 * len(dates_in_window) / expected
    return round(min(100.0, max(0.0, pct)), 2)


def _build_response() -> dict[str, Any]:
    """Compose the Tier-A response. Always returns a parseable dict."""
    now = _now()
    latest = _read_json(LATEST_FILE)
    history = _read_json(HISTORY_FILE)
    if not isinstance(history, list):
        history = []

    operational = isinstance(latest, dict)
    last_active_at = latest.get("generated_at") if operational else None

    return {
        "system": SYSTEM_SLUG,
        "mode": MODE,
        "status": "operational" if operational else "degraded",
        "last_deployed_at": (
            os.environ.get("VERCEL_GIT_COMMIT_AUTHOR_DATE") or last_active_at
        ),
        "last_active_at": last_active_at,
        "uptime_pct_30d": _uptime_pct_30d(history, now),
        "metrics": _metrics(latest if operational else None, history, now),
        "schema_version": SCHEMA_VERSION,
        "generated_at": _now_iso(),
    }


def _degraded_response() -> dict[str, Any]:
    return {
        "system": SYSTEM_SLUG,
        "mode": MODE,
        "status": "degraded",
        "last_deployed_at": None,
        "last_active_at": None,
        "uptime_pct_30d": 0.0,
        "metrics": {
            "datasets_monitored": 0,
            "checks_run_24h": 0,
            "anomalies_detected_24h": 0,
            "schema_drifts_30d": 0,
            "last_check_at": None,
        },
        "schema_version": SCHEMA_VERSION,
        "generated_at": _now_iso(),
    }


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
            payload = _degraded_response()

        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self._write_common_headers()
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt: str, *args: Any) -> None:  # noqa: A002, ARG002
        return  # Suppress default access log; Vercel captures stdout/stderr.
