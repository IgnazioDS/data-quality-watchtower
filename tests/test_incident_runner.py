"""Unit tests for the nightly incident runner (pure-data layer)."""
from __future__ import annotations

import unittest
from datetime import date, datetime, timezone

from data_quality_watchtower import fixtures as fx
from data_quality_watchtower import incident_runner as runner


_FIXED_NOW = datetime(2026, 5, 25, 6, 0, 0, tzinfo=timezone.utc)
_FIXED_DAY = date(2026, 5, 25)


class BuildIncidentTests(unittest.TestCase):
    def test_required_keys_and_schema_version(self) -> None:
        incident, _ = runner.run(day=_FIXED_DAY, now=_FIXED_NOW, history=[])
        runner.validate_incident(incident)  # raises if broken
        for key in runner._REQUIRED_KEYS:
            self.assertIn(key, incident)
        self.assertEqual(incident["schema_version"], 1)
        self.assertEqual(incident["system"], "data-quality-watchtower")

    def test_deterministic_for_a_date(self) -> None:
        first, _ = runner.run(day=_FIXED_DAY, now=_FIXED_NOW, history=[])
        second, _ = runner.run(day=_FIXED_DAY, now=_FIXED_NOW, history=[])
        self.assertEqual(first, second)

    def test_matches_scenario_for_date(self) -> None:
        incident, _ = runner.run(day=_FIXED_DAY, now=_FIXED_NOW, history=[])
        expected = fx.select_scenario_for_date(_FIXED_DAY)
        self.assertEqual(incident["scenario"], expected.key)
        self.assertEqual(incident["run_id"], f"dqw-2026-05-25-{expected.key}")

    def test_metrics_consistent_with_findings(self) -> None:
        incident, _ = runner.run(day=_FIXED_DAY, now=_FIXED_NOW, history=[])
        metrics = incident["metrics"]
        self.assertEqual(metrics["anomalies_detected"], len(incident["findings"]))
        self.assertGreater(metrics["checks_run"], 0)
        self.assertEqual(len(incident["detection_reasons"]), len(incident["findings"]))

    def test_generated_at_uses_now(self) -> None:
        incident, _ = runner.run(day=_FIXED_DAY, now=_FIXED_NOW, history=[])
        self.assertEqual(incident["generated_at"], "2026-05-25T06:00:00Z")

    def test_recent_runs_includes_current(self) -> None:
        incident, _ = runner.run(day=_FIXED_DAY, now=_FIXED_NOW, history=[])
        self.assertEqual(incident["recent_runs"][0]["date"], "2026-05-25")
        self.assertLessEqual(len(incident["recent_runs"]), runner.RECENT_RUNS)


class PreviousRunTests(unittest.TestCase):
    def test_none_on_empty_history(self) -> None:
        incident, _ = runner.run(day=_FIXED_DAY, now=_FIXED_NOW, history=[])
        self.assertIsNone(incident["previous_run"])

    def test_previous_run_and_delta(self) -> None:
        prior = [{
            "run_id": "dqw-2026-05-24-schema_add",
            "generated_at": "2026-05-24T06:00:00Z",
            "scenario": "schema_add",
            "severity": "low",
            "gate_verdict": "pass",
            "drift_detected": True,
        }]
        incident, _ = runner.run(day=_FIXED_DAY, now=_FIXED_NOW, history=prior)
        prev = incident["previous_run"]
        self.assertIsNotNone(prev)
        self.assertEqual(prev["run_id"], "dqw-2026-05-24-schema_add")
        self.assertIn("->", prev["delta"]["severity"])
        self.assertTrue(prev["delta"]["gate_verdict"].startswith("pass ->"))

    def test_skips_same_run_id(self) -> None:
        same_id = runner._run_id(_FIXED_DAY, fx.select_scenario_for_date(_FIXED_DAY).key)
        prior = [{"run_id": same_id, "generated_at": "earlier", "scenario": "x",
                  "severity": "low", "gate_verdict": "pass", "drift_detected": True}]
        self.assertIsNone(runner.compute_previous_run(prior, same_id))


class HistoryTests(unittest.TestCase):
    def test_record_shape(self) -> None:
        incident, _ = runner.run(day=_FIXED_DAY, now=_FIXED_NOW, history=[])
        record = runner.to_history_record(incident)
        self.assertEqual(record["status"], "ok")
        self.assertEqual(record["date"], "2026-05-25")
        self.assertEqual(record["run_id"], incident["run_id"])

    def test_merge_prepends_newest_first(self) -> None:
        a = {"run_id": "a"}
        b = {"run_id": "b"}
        merged = runner.merge_history([a], b)
        self.assertEqual([r["run_id"] for r in merged], ["b", "a"])

    def test_merge_dedupes_same_run_id(self) -> None:
        old = {"run_id": "a", "severity": "low"}
        new = {"run_id": "a", "severity": "high"}
        merged = runner.merge_history([old], new)
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]["severity"], "high")

    def test_merge_trims_to_max(self) -> None:
        history = [{"run_id": f"r{i}"} for i in range(runner.MAX_HISTORY + 50)]
        merged = runner.merge_history(history, {"run_id": "new"})
        self.assertEqual(len(merged), runner.MAX_HISTORY)
        self.assertEqual(merged[0]["run_id"], "new")


class ValidateTests(unittest.TestCase):
    def test_missing_key_raises(self) -> None:
        with self.assertRaises(ValueError):
            runner.validate_incident({"schema_version": 1})

    def test_wrong_schema_version_raises(self) -> None:
        incident, _ = runner.run(day=_FIXED_DAY, now=_FIXED_NOW, history=[])
        broken = {**incident, "schema_version": 2}
        with self.assertRaises(ValueError):
            runner.validate_incident(broken)


if __name__ == "__main__":
    unittest.main()
