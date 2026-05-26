"""Synthetic fixture catalog and CSV loading. Standard library only.

The watchtower monitors a small catalog of committed synthetic datasets: one
stable baseline plus five drift scenarios, each injecting exactly one controlled
failure mode. The nightly cron rotates which scenario it scans by date, so the
public dashboard genuinely detects a different drift each day and the verdict
moves for real rather than averaging to a flat line.

All fixtures are synthetic, seeded, and committed in-repo (see
examples/fixtures/README.md). Any third party can regenerate them bit-for-bit
and reproduce every verdict locally with the engine in watchtower.py.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date
from pathlib import Path

# Repo root is two levels above this package (src/data_quality_watchtower/).
_REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURES_DIR = _REPO_ROOT / "examples" / "fixtures"

BASELINE_FILENAME = "orders_baseline.csv"
BASELINE_NAME = "orders"


@dataclass(frozen=True)
class Scenario:
    """One drift scenario: a baseline variant with one injected failure.

    ``expected_category`` is the ProfileComparison attribute that must be
    non-empty when watchtower.compare_profiles runs this scenario against the
    baseline. It is the contract the fixture-integrity test enforces.
    """

    key: str
    title: str
    description: str
    expected_category: str
    filename: str


# Ordered catalog. The cron rotates across this tuple by date.
SCENARIOS: tuple[Scenario, ...] = (
    Scenario(
        key="schema_add",
        title="Schema add",
        description="An upstream producer adds an unexpected column.",
        expected_category="added_columns",
        filename="orders_drift_schema_add.csv",
    ),
    Scenario(
        key="null_rate_shift",
        title="Null-rate shift",
        description="A reliably populated column starts arriving mostly empty.",
        expected_category="null_rate_drifts",
        filename="orders_drift_null_rate.csv",
    ),
    Scenario(
        key="value_distribution_shift",
        title="Value-distribution shift",
        description="A billing column collapses toward zero.",
        expected_category="numeric_drifts",
        filename="orders_drift_value_distribution.csv",
    ),
    Scenario(
        key="cardinality_collapse",
        title="Cardinality collapse",
        description="A foreign key loses most of its unique values.",
        expected_category="cardinality_drifts",
        filename="orders_drift_cardinality_collapse.csv",
    ),
    Scenario(
        key="type_coercion",
        title="Type coercion",
        description="A numeric column starts arriving as free text.",
        expected_category="type_changes",
        filename="orders_drift_type_coercion.csv",
    ),
)

_SCENARIOS_BY_KEY = {scenario.key: scenario for scenario in SCENARIOS}


def datasets_monitored() -> int:
    """Distinct datasets under monitoring: the baseline plus each variant."""
    return 1 + len(SCENARIOS)


def select_scenario_for_date(day: date) -> Scenario:
    """Deterministically pick the scenario for a calendar date.

    Uses the proleptic Gregorian ordinal so the rotation is stable, reproducible
    from the date alone, and cycles through every scenario over the catalog
    length in days.
    """
    return SCENARIOS[day.toordinal() % len(SCENARIOS)]


def scenario_by_key(key: str) -> Scenario:
    try:
        return _SCENARIOS_BY_KEY[key]
    except KeyError as exc:
        raise ValueError(f"Unknown scenario key: {key!r}") from exc


def baseline_path() -> Path:
    return FIXTURES_DIR / BASELINE_FILENAME


def scenario_path(scenario: Scenario) -> Path:
    return FIXTURES_DIR / scenario.filename


def load_csv(path: Path) -> tuple[list[str], list[list[str]]]:
    """Load a CSV into (header, rows). Raises FileNotFoundError if absent."""
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        rows = list(reader)
    if not rows:
        return [], []
    return rows[0], rows[1:]
