"""Unit tests for the /api/incident-latest serverless function.

The file is api/incident-latest.py (hyphenated to match the canonical route),
so it is loaded by path rather than by import name.
"""
from __future__ import annotations

import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

_API = Path(__file__).resolve().parent.parent / "api" / "incident-latest.py"
_spec = importlib.util.spec_from_file_location("incident_latest", _API)
incident_latest = importlib.util.module_from_spec(_spec)
assert _spec and _spec.loader
_spec.loader.exec_module(incident_latest)


_SEED = {
    "system": "data-quality-watchtower",
    "schema_version": 1,
    "run_id": "dqw-2026-05-26-value_distribution_shift",
    "fixture": "orders",
    "scenario": "value_distribution_shift",
    "drift_detected": True,
    "severity": "critical",
    "gate_verdict": "fail",
    "detection_reasons": ["Column `revenue_usd` mean shifted ..."],
    "report_url": "https://github.com/IgnazioDS/data-quality-watchtower/blob/main/reports/incident-2026-05-26.md",
    "generated_at": "2026-05-26T06:00:00Z",
    "previous_run": None,
}


class BuildResponseTests(unittest.TestCase):
    def setUp(self) -> None:
        self._orig = incident_latest.LATEST_FILE

    def tearDown(self) -> None:
        incident_latest.LATEST_FILE = self._orig

    def test_serves_artifact_verbatim(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "latest.json"
            path.write_text(json.dumps(_SEED), encoding="utf-8")
            incident_latest.LATEST_FILE = path
            response = incident_latest._build_response()
        self.assertEqual(response["run_id"], _SEED["run_id"])
        self.assertEqual(response["severity"], "critical")
        self.assertEqual(response["schema_version"], 1)
        self.assertEqual(response["benchmark_type"], "drift")
        self.assertIn("previous_run", response)

    def test_degraded_when_missing(self) -> None:
        incident_latest.LATEST_FILE = Path("/nonexistent/latest.json")
        response = incident_latest._build_response()
        self.assertEqual(response["status"], "degraded")
        self.assertEqual(response["schema_version"], 1)
        self.assertEqual(response["benchmark_type"], "drift")
        self.assertFalse(response["drift_detected"])
        self.assertIn("previous_run", response)
        self.assertIsNone(response["previous_run"])

    def test_rejects_wrong_schema_version(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "latest.json"
            path.write_text(json.dumps({**_SEED, "schema_version": 2}), encoding="utf-8")
            incident_latest.LATEST_FILE = path
            response = incident_latest._build_response()
        self.assertEqual(response["status"], "degraded")  # falls back, never serves v2


class HandlerTests(unittest.TestCase):
    def _invoke(self, method: str = "GET") -> tuple[int, dict[str, str], bytes]:
        wfile = io.BytesIO()
        h = incident_latest.handler.__new__(incident_latest.handler)
        h.wfile = wfile
        h.client_address = ("127.0.0.1", 0)
        h.server = MagicMock()
        h.command = method
        h.path = "/api/incident-latest"
        h.request_version = "HTTP/1.0"
        h.headers = {}
        h.requestline = f"{method} /api/incident-latest HTTP/1.0"

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
        self.assertEqual(payload["benchmark_type"], "drift")
        self.assertIn("previous_run", payload)

    def test_options_returns_204(self) -> None:
        status, headers, _ = self._invoke("OPTIONS")
        self.assertEqual(status, 204)
        self.assertEqual(headers.get("Access-Control-Allow-Methods"), "GET, OPTIONS")


if __name__ == "__main__":
    unittest.main()
