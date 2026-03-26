from __future__ import annotations

import unittest

from data_quality_watchtower.cli import run


class CliTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
