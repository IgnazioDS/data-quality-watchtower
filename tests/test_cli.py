from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from data_quality_watchtower.cli import run


class CliTests(unittest.TestCase):
    def setUp(self) -> None:
        repo_root = Path(__file__).resolve().parent.parent
        self.orders = str(repo_root / "examples" / "orders.csv")
        self.orders_drifted = str(repo_root / "examples" / "orders_drifted.csv")

    def test_summary(self) -> None:
        output = run(["summary"])
        self.assertIn("Data Quality Watchtower", output)
        self.assertIn("Data issues usually surface downstream after dashboards, models, or reports are already wrong.", output)

    def test_capabilities(self) -> None:
        output = run(["capabilities"])
        self.assertIn("Core capabilities:", output)
        self.assertIn("Profile tabular datasets and schemas", output)

    def test_roadmap(self) -> None:
        output = run(["roadmap"])
        self.assertIn("# Roadmap", output)
        self.assertIn("## Phase 1", output)

    def test_profile_command_json(self) -> None:
        output = run(["profile", self.orders, "--format", "json"])
        payload = json.loads(output)

        self.assertEqual(payload["row_count"], 12)
        self.assertEqual(payload["column_count"], 7)

    def test_profile_command_writes_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "baseline.json"
            output = run(["profile", self.orders, "--output", str(output_path)])

            self.assertTrue(output_path.exists())
            self.assertIn("Saved profile:", output)

    def test_compare_command_detects_incident(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            baseline = Path(tmpdir) / "baseline.json"
            candidate = Path(tmpdir) / "candidate.json"
            run(["profile", self.orders, "--output", str(baseline), "--format", "json"])
            run(["profile", self.orders_drifted, "--output", str(candidate), "--format", "json"])
            output = run(["compare", str(baseline), str(candidate)])

            self.assertIn("Severity: critical", output)
            self.assertIn("coupon_code", output)
            self.assertIn("customer_id", output)

    def test_compare_command_json_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            baseline = Path(tmpdir) / "baseline.json"
            candidate = Path(tmpdir) / "candidate.json"
            report = Path(tmpdir) / "comparison.json"
            run(["profile", self.orders, "--output", str(baseline), "--format", "json"])
            run(["profile", self.orders_drifted, "--output", str(candidate), "--format", "json"])
            output = run(["compare", str(baseline), str(candidate), "--format", "json", "--report", str(report)])
            payload = json.loads(output)

            self.assertTrue(report.exists())
            self.assertEqual(payload["incident_severity"], "critical")


if __name__ == "__main__":
    unittest.main()
