"""Generate the synthetic fixture catalog. Standard library only.

Writes one stable baseline orders dataset plus five drift scenarios, each
injecting exactly one controlled failure mode the comparator is built to catch.
Everything is seeded, so re-running this script reproduces the committed CSVs
bit-for-bit:

    python3 scripts/generate_fixtures.py

The fixtures are synthetic. No real customer, billing, or PII data is involved.
See examples/fixtures/README.md for the provenance and per-scenario contract.
"""
from __future__ import annotations

import csv
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "examples" / "fixtures"

SEED = 1111
ROWS = 500

HEADER = [
    "order_id",
    "customer_id",
    "product_sku",
    "quantity",
    "unit_price",
    "revenue_usd",
    "currency",
    "status",
    "region",
    "created_at",
]

_SKUS = [f"SKU-{i:04d}" for i in range(1, 41)]
_STATUSES = ["paid"] * 70 + ["pending"] * 15 + ["refunded"] * 10 + ["cancelled"] * 5
# Region codes avoid "NA", which a data-quality profiler correctly reads as a
# null token. Using it as a category value would be ambiguous by design.
_REGIONS = ["AMER"] * 45 + ["EMEA"] * 30 + ["APAC"] * 18 + ["LATAM"] * 7
_CURRENCIES = ["USD"] * 96 + ["EUR"] * 3 + ["GBP"] * 1
_CUSTOMER_POOL = 450  # ~450 possible ids across 500 rows keeps cardinality high
_BASE_TIME = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _make_baseline(rng: random.Random) -> list[list[str]]:
    rows: list[list[str]] = []
    for i in range(ROWS):
        quantity = rng.randint(1, 12)
        unit_price = round(rng.uniform(5.0, 500.0), 2)
        revenue = round(quantity * unit_price, 2)
        # region is reliably populated: roughly 2 percent null in the baseline.
        region = "" if rng.random() < 0.02 else rng.choice(_REGIONS)
        created = _BASE_TIME + timedelta(minutes=rng.randint(0, 120 * 24 * 60))
        rows.append([
            f"ORD-{100000 + i}",
            f"CUST-{rng.randint(1, _CUSTOMER_POOL):05d}",
            rng.choice(_SKUS),
            str(quantity),
            f"{unit_price:.2f}",
            f"{revenue:.2f}",
            rng.choice(_CURRENCIES),
            rng.choice(_STATUSES),
            region,
            created.strftime("%Y-%m-%dT%H:%M:%SZ"),
        ])
    return rows


def _col(name: str) -> int:
    return HEADER.index(name)


def _copy(rows: list[list[str]]) -> list[list[str]]:
    return [list(row) for row in rows]


def _drift_schema_add(rows: list[list[str]], rng: random.Random) -> tuple[list[str], list[list[str]]]:
    """Add an unexpected column. The baseline column set is untouched."""
    header = HEADER + ["discount_code"]
    codes = ["", "SAVE10", "WELCOME", "VIP", "BULK20"]
    out = [row + [rng.choice(codes)] for row in _copy(rows)]
    return header, out


def _drift_null_rate(rows: list[list[str]], rng: random.Random) -> tuple[list[str], list[list[str]]]:
    """Blank out region in roughly 40 percent of rows."""
    out = _copy(rows)
    region_idx = _col("region")
    for row in out:
        if rng.random() < 0.40:
            row[region_idx] = ""
    return list(HEADER), out


def _drift_value_distribution(rows: list[list[str]], rng: random.Random) -> tuple[list[str], list[list[str]]]:
    """Collapse revenue_usd toward zero for ~90 percent of rows.

    unit_price and quantity are left intact, so revenue no longer equals
    quantity times unit_price. This is the plausible-but-wrong shift: the
    column type is unchanged and the rows still parse.
    """
    out = _copy(rows)
    revenue_idx = _col("revenue_usd")
    for row in out:
        if rng.random() < 0.95:
            collapsed = round(float(row[revenue_idx]) * 0.13, 2)
            row[revenue_idx] = f"{collapsed:.2f}"
    return list(HEADER), out


def _drift_cardinality_collapse(rows: list[list[str]], rng: random.Random) -> tuple[list[str], list[list[str]]]:
    """Remap customer_id onto only 15 distinct values."""
    out = _copy(rows)
    customer_idx = _col("customer_id")
    for row in out:
        row[customer_idx] = f"CUST-{rng.randint(1, 15):05d}"
    return list(HEADER), out


def _drift_type_coercion(rows: list[list[str]], rng: random.Random) -> tuple[list[str], list[list[str]]]:
    """Turn quantity into free text for ~60 percent of rows."""
    out = _copy(rows)
    quantity_idx = _col("quantity")
    words = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five"}
    for row in out:
        if rng.random() < 0.60:
            value = int(row[quantity_idx])
            row[quantity_idx] = words.get(value, f"{value} units")
    return list(HEADER), out


_DRIFTS = [
    ("orders_drift_schema_add.csv", _drift_schema_add),
    ("orders_drift_null_rate.csv", _drift_null_rate),
    ("orders_drift_value_distribution.csv", _drift_value_distribution),
    ("orders_drift_cardinality_collapse.csv", _drift_cardinality_collapse),
    ("orders_drift_type_coercion.csv", _drift_type_coercion),
]


def _write(filename: str, header: list[str], rows: list[list[str]]) -> None:
    path = OUT_DIR / filename
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        writer.writerows(rows)
    print(f"wrote {path.relative_to(ROOT)}: {len(rows)} rows, {len(header)} cols")


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rng = random.Random(SEED)
    baseline = _make_baseline(rng)
    _write("orders_baseline.csv", list(HEADER), baseline)
    for filename, drift in _DRIFTS:
        header, rows = drift(baseline, rng)
        _write(filename, header, rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
