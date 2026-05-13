from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from data_quality_watchtower.watchtower import assess_gate, compare_profiles, load_profile, profile_dataset, profile_to_dict, save_json


class WatchtowerTests(unittest.TestCase):
    def setUp(self) -> None:
        repo_root = Path(__file__).resolve().parent.parent
        self.orders = repo_root / "examples" / "orders.csv"
        self.orders_drifted = repo_root / "examples" / "orders_drifted.csv"

    def test_profile_dataset_builds_schema_fingerprint(self) -> None:
        profile = profile_dataset(self.orders)
        revenue = next(column for column in profile.columns if column.name == "revenue_usd")
        region = next(column for column in profile.columns if column.name == "region")

        self.assertEqual(profile.row_count, 12)
        self.assertEqual(profile.column_count, 7)
        self.assertEqual(revenue.inferred_type, "float")
        self.assertIsNotNone(revenue.numeric_summary)
        self.assertEqual(len(profile.schema_fingerprint), 16)
        self.assertGreater(region.unique_ratio, 0)
        self.assertGreater(len(region.top_values), 0)

    def test_load_profile_round_trip(self) -> None:
        with TemporaryDirectory() as tmpdir:
            output = Path(tmpdir) / "baseline.json"
            save_json(profile_to_dict(profile_dataset(self.orders)), output)
            loaded = load_profile(output)

            self.assertEqual(loaded.row_count, 12)
            self.assertEqual(loaded.columns[0].name, "order_id")

    def test_compare_profiles_detects_material_drift(self) -> None:
        with TemporaryDirectory() as tmpdir:
            baseline_path = Path(tmpdir) / "baseline.json"
            candidate_path = Path(tmpdir) / "candidate.json"
            save_json(profile_to_dict(profile_dataset(self.orders)), baseline_path)
            save_json(profile_to_dict(profile_dataset(self.orders_drifted)), candidate_path)

            comparison = compare_profiles(baseline_path, candidate_path)

            self.assertEqual(comparison.incident_severity, "critical")
            self.assertIn("coupon_code", comparison.added_columns)
            self.assertIn("region", comparison.removed_columns)
            self.assertTrue(any(item["column"] == "customer_id" for item in comparison.type_changes))
            self.assertTrue(any(item["column"] == "discount_pct" for item in comparison.null_rate_drifts))
            self.assertTrue(any(item["column"] == "revenue_usd" for item in comparison.numeric_drifts))
            self.assertTrue(any(item["column"] == "discount_pct" for item in comparison.cardinality_drifts))
            self.assertIn("Critical incident", comparison.incident_summary)

    def test_assess_gate_fails_on_drift(self) -> None:
        with TemporaryDirectory() as tmpdir:
            baseline_path = Path(tmpdir) / "baseline.json"
            candidate_path = Path(tmpdir) / "candidate.json"
            save_json(profile_to_dict(profile_dataset(self.orders)), baseline_path)
            save_json(profile_to_dict(profile_dataset(self.orders_drifted)), candidate_path)
            comparison = compare_profiles(baseline_path, candidate_path)
            gate = assess_gate(comparison, allowed_severity="warning")

            self.assertFalse(gate.passed)
            self.assertGreater(len(gate.reasons), 0)


if __name__ == "__main__":
    unittest.main()
