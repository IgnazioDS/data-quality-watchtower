"""Unit tests for the /api/stats Tier-A live telemetry function.

The endpoint reads the committed incident artifacts (no network, no secrets)
and reports the real drift-scan workload. Covers: live response shape, the
24h/30d windowing, the uptime measure, degraded behaviour when artifacts are
missing, safety caps, and the never-5xx handler contract.
"""
from __future__ import annotations

import io
import json
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock

# Add repo root /api to sys.path so we can import the api/stats.py module.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "api"))
import stats  # type: ignore  # noqa: E402

_NOW = datetime(2026, 5, 26, 12, 0, 0, tzinfo=timezone.utc)


def _iso(moment: datetime) -> str:
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


def _record(when: datetime, checks: int, anomalies: int, schema: int) -> dict:
    return {
        "run_id": f"r-{when.date()}",
        "generated_at": _iso(when),
        "scenario": "value_distribution_shift",
        "severity": "critical",
        "gate_verdict": "fail",
        "drift_detected": True,
        "checks_run": checks,
        "anomalies_detected": anomalies,
        "schema_drift_count": schema,
        "status": "ok",
    }


class MetricsWindowTests(unittest.TestCase):
    def test_windows_sum_correctly(self) -> None:
        latest = {"datasets_monitored": 6, "generated_at": _iso(_NOW - timedelta(hours=1))}
        history = [
            _record(_NOW - timedelta(hours=1), checks=50, anomalies=1, schema=0),
            _record(_NOW - timedelta(days=2), checks=30, anomalies=2, schema=1),
            _record(_NOW - timedelta(days=40), checks=99, anomalies=9, schema=9),
        ]
        metrics = stats._metrics(latest, history, _NOW)
        self.assertEqual(metrics["datasets_monitored"], 6)
        self.assertEqual(metrics["checks_run_24h"], 50)  # only the 1h-old run
        self.assertEqual(metrics["anomalies_detected_24h"], 1)
        self.assertEqual(metrics["schema_drifts_30d"], 1)  # 1h + 2d, not 40d
        self.assertEqual(metrics["last_check_at"], latest["generated_at"])

    def test_safety_cap_clamps(self) -> None:
        latest = {"datasets_monitored": 9_999_999, "generated_at": _iso(_NOW)}
        metrics = stats._metrics(latest, [], _NOW)
        self.assertEqual(metrics["datasets_monitored"], 1_000_000)

    def test_cap_helper(self) -> None:
        self.assertEqual(stats._cap("checks_run_24h", 5_000_000), 1_000_000)
        self.assertEqual(stats._cap("unknown", 42), 42)


class UptimeTests(unittest.TestCase):
    def test_full_uptime_no_gaps(self) -> None:
        history = [_record(_NOW - timedelta(days=d), 50, 1, 0) for d in range(3)]
        self.assertEqual(stats._uptime_pct_30d(history, _NOW), 100.0)

    def test_gap_lowers_uptime(self) -> None:
        history = [
            _record(_NOW, 50, 1, 0),
            _record(_NOW - timedelta(days=2), 50, 1, 0),
        ]  # first run 2 days ago, only 2 of 3 expected days ran
        self.assertEqual(stats._uptime_pct_30d(history, _NOW), 66.67)

    def test_empty_history_is_zero(self) -> None:
        self.assertEqual(stats._uptime_pct_30d([], _NOW), 0.0)


class BuildResponseTests(unittest.TestCase):
    def setUp(self) -> None:
        self._orig_latest = stats.LATEST_FILE
        self._orig_history = stats.HISTORY_FILE

    def tearDown(self) -> None:
        stats.LATEST_FILE = self._orig_latest
        stats.HISTORY_FILE = self._orig_history

    def _seed(self, tmp: Path) -> None:
        latest = {
            "system": "data-quality-watchtower",
            "schema_version": 1,
            "datasets_monitored": 6,
            "generated_at": _iso(_NOW),
        }
        history = [_record(_NOW, 50, 1, 0)]
        (tmp / "latest.json").write_text(json.dumps(latest), encoding="utf-8")
        (tmp / "history.json").write_text(json.dumps(history), encoding="utf-8")
        stats.LATEST_FILE = tmp / "latest.json"
        stats.HISTORY_FILE = tmp / "history.json"

    def test_operational_live(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as d:
            self._seed(Path(d))
            response = stats._build_response()
        self.assertEqual(response["mode"], "live")
        self.assertEqual(response["status"], "operational")
        self.assertEqual(response["schema_version"], 1)
        self.assertEqual(response["system"], "data-quality-watchtower")
        self.assertEqual(set(response["metrics"]), {
            "datasets_monitored", "checks_run_24h", "anomalies_detected_24h",
            "schema_drifts_30d", "last_check_at",
        })
        self.assertIsNotNone(response["last_active_at"])
        self.assertTrue(response["generated_at"].endswith("Z"))

    def test_degraded_when_missing(self) -> None:
        stats.LATEST_FILE = Path("/nonexistent/latest.json")
        stats.HISTORY_FILE = Path("/nonexistent/history.json")
        response = stats._build_response()
        self.assertEqual(response["mode"], "live")
        self.assertEqual(response["status"], "degraded")
        self.assertEqual(response["metrics"]["datasets_monitored"], 0)
        self.assertIsNone(response["metrics"]["last_check_at"])
        self.assertEqual(response["schema_version"], 1)


class HandlerTests(unittest.TestCase):
    def _invoke(self, method: str = "GET") -> tuple[int, dict[str, str], bytes]:
        wfile = io.BytesIO()
        h = stats.handler.__new__(stats.handler)
        h.wfile = wfile
        h.client_address = ("127.0.0.1", 0)
        h.server = MagicMock()
        h.command = method
        h.path = "/api/stats"
        h.request_version = "HTTP/1.0"
        h.headers = {}
        h.requestline = f"{method} /api/stats HTTP/1.0"

        if method == "OPTIONS":
            h.do_OPTIONS()
        else:
            h.do_GET()

        raw = wfile.getvalue().decode("utf-8", errors="replace")
        head, _, body = raw.partition("\r\n\r\n")
        status_code = int(head.split("\r\n", 1)[0].split(" ", 2)[1])
        headers = {}
        for line in head.split("\r\n")[1:]:
            if ": " in line:
                key, value = line.split(": ", 1)
                headers[key] = value
        return status_code, headers, body.encode("utf-8")

    def test_get_returns_200_and_valid_json(self) -> None:
        status, headers, body = self._invoke("GET")
        self.assertEqual(status, 200)
        self.assertEqual(headers.get("Content-Type"), "application/json")
        self.assertEqual(headers.get("Access-Control-Allow-Origin"), "*")
        self.assertIn("max-age=30", headers.get("Cache-Control", ""))
        payload = json.loads(body)
        self.assertEqual(payload["schema_version"], 1)
        self.assertEqual(payload["mode"], "live")

    def test_options_returns_204(self) -> None:
        status, headers, _ = self._invoke("OPTIONS")
        self.assertEqual(status, 204)
        self.assertEqual(headers.get("Access-Control-Allow-Methods"), "GET, OPTIONS")


if __name__ == "__main__":
    unittest.main()
