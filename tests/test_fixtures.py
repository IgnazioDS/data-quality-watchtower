"""Unit tests for the fixture catalog and the date-based scenario rotation.

The scenario-file tests double as an integration check against the engine in
watchtower.py: each committed fixture must still trigger the comparison
category it claims, so a regeneration that breaks a scenario fails CI.
"""
from __future__ import annotations

import unittest
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory

from data_quality_watchtower import fixtures as fx
from data_quality_watchtower.watchtower import (
    compare_profiles,
    profile_dataset,
    profile_to_dict,
    save_json,
)


def _compare(baseline_csv: Path, candidate_csv: Path, tmp: str):
    baseline_json = Path(tmp) / "baseline.json"
    candidate_json = Path(tmp) / "candidate.json"
    save_json(profile_to_dict(profile_dataset(baseline_csv)), baseline_json)
    save_json(profile_to_dict(profile_dataset(candidate_csv)), candidate_json)
    return compare_profiles(baseline_json, candidate_json)


class RotationTests(unittest.TestCase):
    def test_deterministic_for_a_date(self) -> None:
        day = date(2026, 5, 25)
        self.assertEqual(
            fx.select_scenario_for_date(day), fx.select_scenario_for_date(day)
        )

    def test_cycles_through_whole_catalog(self) -> None:
        start = date(2026, 1, 1)
        picked = {
            fx.select_scenario_for_date(date.fromordinal(start.toordinal() + offset)).key
            for offset in range(len(fx.SCENARIOS))
        }
        self.assertEqual(picked, {s.key for s in fx.SCENARIOS})

    def test_consecutive_days_differ(self) -> None:
        day = date(2026, 5, 25)
        nxt = date.fromordinal(day.toordinal() + 1)
        self.assertNotEqual(
            fx.select_scenario_for_date(day).key,
            fx.select_scenario_for_date(nxt).key,
        )


class CatalogTests(unittest.TestCase):
    def test_datasets_monitored(self) -> None:
        self.assertEqual(fx.datasets_monitored(), 1 + len(fx.SCENARIOS))

    def test_keys_are_unique(self) -> None:
        keys = [s.key for s in fx.SCENARIOS]
        self.assertEqual(len(keys), len(set(keys)))

    def test_scenario_by_key_roundtrip(self) -> None:
        for scenario in fx.SCENARIOS:
            self.assertIs(fx.scenario_by_key(scenario.key), scenario)

    def test_unknown_key_raises(self) -> None:
        with self.assertRaises(ValueError):
            fx.scenario_by_key("does-not-exist")


class FixtureFileTests(unittest.TestCase):
    def test_baseline_loads_with_expected_shape(self) -> None:
        profile = profile_dataset(fx.baseline_path())
        self.assertEqual(profile.row_count, 500)
        names = {column.name for column in profile.columns}
        self.assertIn("revenue_usd", names)
        region = next(c for c in profile.columns if c.name == "region")
        # region is a reliably-populated category in the baseline
        self.assertLess(region.null_rate, 0.10)
        self.assertEqual(region.unique_count, 4)

    def test_each_scenario_triggers_its_category(self) -> None:
        baseline = fx.baseline_path()
        for scenario in fx.SCENARIOS:
            with TemporaryDirectory() as tmp:
                comparison = _compare(baseline, fx.scenario_path(scenario), tmp)
            detected = getattr(comparison, scenario.expected_category)
            self.assertTrue(detected, f"{scenario.key}: {scenario.expected_category} empty")


if __name__ == "__main__":
    unittest.main()
