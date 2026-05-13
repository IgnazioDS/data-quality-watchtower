from __future__ import annotations

import csv
import hashlib
import json
import math
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class NumericSummary:
    min_value: float
    max_value: float
    mean: float
    median: float
    p05: float
    p95: float
    outlier_count: int
    outlier_rate: float


@dataclass(frozen=True)
class ColumnProfile:
    name: str
    inferred_type: str
    null_count: int
    null_rate: float
    unique_count: int
    sample_values: list[str]
    numeric_summary: NumericSummary | None


@dataclass(frozen=True)
class DatasetProfile:
    dataset_path: str
    generated_at: str
    row_count: int
    column_count: int
    schema_fingerprint: str
    columns: list[ColumnProfile]


@dataclass(frozen=True)
class ProfileComparison:
    baseline_profile: str
    candidate_profile: str
    baseline_row_count: int
    candidate_row_count: int
    row_count_delta: int
    row_count_delta_ratio: float
    added_columns: list[str]
    removed_columns: list[str]
    type_changes: list[dict[str, str]]
    null_rate_drifts: list[dict[str, Any]]
    numeric_drifts: list[dict[str, Any]]
    incident_summary: str
    incident_severity: str


def profile_dataset(csv_path: str | Path) -> DatasetProfile:
    path = Path(csv_path)
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError("CSV file must include a header row.")
        fieldnames = [name.strip() for name in reader.fieldnames]
        rows = [{key.strip(): value for key, value in row.items()} for row in reader]

    columns = [_profile_column(field, rows) for field in fieldnames]
    fingerprint = _schema_fingerprint(columns)
    return DatasetProfile(
        dataset_path=str(path),
        generated_at=datetime.now(tz=UTC).isoformat().replace("+00:00", "Z"),
        row_count=len(rows),
        column_count=len(fieldnames),
        schema_fingerprint=fingerprint,
        columns=columns,
    )


def load_profile(profile_path: str | Path) -> DatasetProfile:
    payload = json.loads(Path(profile_path).read_text(encoding="utf-8"))
    columns = [
        ColumnProfile(
            name=item["name"],
            inferred_type=item["inferred_type"],
            null_count=int(item["null_count"]),
            null_rate=float(item["null_rate"]),
            unique_count=int(item["unique_count"]),
            sample_values=[str(value) for value in item["sample_values"]],
            numeric_summary=(
                NumericSummary(
                    min_value=float(item["numeric_summary"]["min_value"]),
                    max_value=float(item["numeric_summary"]["max_value"]),
                    mean=float(item["numeric_summary"]["mean"]),
                    median=float(item["numeric_summary"]["median"]),
                    p05=float(item["numeric_summary"]["p05"]),
                    p95=float(item["numeric_summary"]["p95"]),
                    outlier_count=int(item["numeric_summary"]["outlier_count"]),
                    outlier_rate=float(item["numeric_summary"]["outlier_rate"]),
                )
                if item.get("numeric_summary") is not None
                else None
            ),
        )
        for item in payload["columns"]
    ]
    return DatasetProfile(
        dataset_path=str(payload["dataset_path"]),
        generated_at=str(payload["generated_at"]),
        row_count=int(payload["row_count"]),
        column_count=int(payload["column_count"]),
        schema_fingerprint=str(payload["schema_fingerprint"]),
        columns=columns,
    )


def compare_profiles(
    baseline_profile_path: str | Path,
    candidate_profile_path: str | Path,
) -> ProfileComparison:
    baseline = load_profile(baseline_profile_path)
    candidate = load_profile(candidate_profile_path)

    baseline_columns = {column.name: column for column in baseline.columns}
    candidate_columns = {column.name: column for column in candidate.columns}

    added_columns = sorted(set(candidate_columns) - set(baseline_columns))
    removed_columns = sorted(set(baseline_columns) - set(candidate_columns))

    type_changes: list[dict[str, str]] = []
    null_rate_drifts: list[dict[str, Any]] = []
    numeric_drifts: list[dict[str, Any]] = []

    shared_columns = sorted(set(baseline_columns) & set(candidate_columns))
    for name in shared_columns:
        base = baseline_columns[name]
        cand = candidate_columns[name]
        if base.inferred_type != cand.inferred_type:
            type_changes.append(
                {
                    "column": name,
                    "baseline_type": base.inferred_type,
                    "candidate_type": cand.inferred_type,
                }
            )

        null_delta = round(cand.null_rate - base.null_rate, 3)
        if abs(null_delta) >= 0.05:
            null_rate_drifts.append(
                {
                    "column": name,
                    "baseline_null_rate": base.null_rate,
                    "candidate_null_rate": cand.null_rate,
                    "delta": null_delta,
                }
            )

        if base.numeric_summary and cand.numeric_summary:
            mean_delta_ratio = _ratio_delta(base.numeric_summary.mean, cand.numeric_summary.mean)
            outlier_delta = round(
                cand.numeric_summary.outlier_rate - base.numeric_summary.outlier_rate,
                3,
            )
            if abs(mean_delta_ratio) >= 0.2 or abs(outlier_delta) >= 0.05:
                numeric_drifts.append(
                    {
                        "column": name,
                        "baseline_mean": round(base.numeric_summary.mean, 3),
                        "candidate_mean": round(cand.numeric_summary.mean, 3),
                        "mean_delta_ratio": mean_delta_ratio,
                        "baseline_outlier_rate": base.numeric_summary.outlier_rate,
                        "candidate_outlier_rate": cand.numeric_summary.outlier_rate,
                        "outlier_delta": outlier_delta,
                    }
                )

    row_count_delta = candidate.row_count - baseline.row_count
    row_count_delta_ratio = _ratio_delta(float(baseline.row_count), float(candidate.row_count))
    incident_summary, severity = _incident_report(
        baseline=baseline,
        candidate=candidate,
        added_columns=added_columns,
        removed_columns=removed_columns,
        type_changes=type_changes,
        null_rate_drifts=null_rate_drifts,
        numeric_drifts=numeric_drifts,
    )

    return ProfileComparison(
        baseline_profile=str(baseline_profile_path),
        candidate_profile=str(candidate_profile_path),
        baseline_row_count=baseline.row_count,
        candidate_row_count=candidate.row_count,
        row_count_delta=row_count_delta,
        row_count_delta_ratio=row_count_delta_ratio,
        added_columns=added_columns,
        removed_columns=removed_columns,
        type_changes=type_changes,
        null_rate_drifts=sorted(null_rate_drifts, key=lambda item: abs(item["delta"]), reverse=True),
        numeric_drifts=sorted(
            numeric_drifts,
            key=lambda item: max(abs(item["mean_delta_ratio"]), abs(item["outlier_delta"])),
            reverse=True,
        ),
        incident_summary=incident_summary,
        incident_severity=severity,
    )


def format_profile(profile: DatasetProfile) -> str:
    lines = [
        f"Profile {profile.dataset_path}",
        f"Rows: {profile.row_count}",
        f"Columns: {profile.column_count}",
        f"Schema fingerprint: {profile.schema_fingerprint}",
        "",
        "Columns:",
    ]
    for column in profile.columns:
        lines.append(
            f"- {column.name} [{column.inferred_type}] null_rate={column.null_rate:.3f} unique={column.unique_count}"
        )
        if column.numeric_summary:
            lines.append(
                (
                    "  numeric: "
                    f"mean={column.numeric_summary.mean:.3f} "
                    f"median={column.numeric_summary.median:.3f} "
                    f"range={column.numeric_summary.min_value:.3f}..{column.numeric_summary.max_value:.3f} "
                    f"outliers={column.numeric_summary.outlier_count}"
                )
            )
    return "\n".join(lines)


def format_comparison(comparison: ProfileComparison) -> str:
    lines = [
        f"Compare {comparison.baseline_profile} -> {comparison.candidate_profile}",
        f"Severity: {comparison.incident_severity}",
        f"Rows: {comparison.baseline_row_count} -> {comparison.candidate_row_count} ({comparison.row_count_delta:+d}, {comparison.row_count_delta_ratio:+.3f})",
        f"Incident: {comparison.incident_summary}",
        "",
        f"Added columns: {', '.join(comparison.added_columns) if comparison.added_columns else 'none'}",
        f"Removed columns: {', '.join(comparison.removed_columns) if comparison.removed_columns else 'none'}",
        "",
        f"Type changes: {len(comparison.type_changes)}",
    ]
    lines.extend(
        f"- {item['column']}: {item['baseline_type']} -> {item['candidate_type']}"
        for item in comparison.type_changes
    )
    lines.extend(["", f"Null-rate drifts: {len(comparison.null_rate_drifts)}"])
    lines.extend(
        (
            f"- {item['column']}: "
            f"{item['baseline_null_rate']:.3f} -> {item['candidate_null_rate']:.3f} "
            f"({item['delta']:+.3f})"
        )
        for item in comparison.null_rate_drifts[:10]
    )
    lines.extend(["", f"Numeric drifts: {len(comparison.numeric_drifts)}"])
    lines.extend(
        (
            f"- {item['column']}: "
            f"mean {item['baseline_mean']:.3f} -> {item['candidate_mean']:.3f} "
            f"({item['mean_delta_ratio']:+.3f}), "
            f"outliers {item['baseline_outlier_rate']:.3f} -> {item['candidate_outlier_rate']:.3f}"
        )
        for item in comparison.numeric_drifts[:10]
    )
    return "\n".join(lines)


def profile_to_dict(profile: DatasetProfile) -> dict[str, Any]:
    return {
        "dataset_path": profile.dataset_path,
        "generated_at": profile.generated_at,
        "row_count": profile.row_count,
        "column_count": profile.column_count,
        "schema_fingerprint": profile.schema_fingerprint,
        "columns": [column_to_dict(column) for column in profile.columns],
    }


def comparison_to_dict(comparison: ProfileComparison) -> dict[str, Any]:
    return {
        "baseline_profile": comparison.baseline_profile,
        "candidate_profile": comparison.candidate_profile,
        "baseline_row_count": comparison.baseline_row_count,
        "candidate_row_count": comparison.candidate_row_count,
        "row_count_delta": comparison.row_count_delta,
        "row_count_delta_ratio": comparison.row_count_delta_ratio,
        "added_columns": comparison.added_columns,
        "removed_columns": comparison.removed_columns,
        "type_changes": comparison.type_changes,
        "null_rate_drifts": comparison.null_rate_drifts,
        "numeric_drifts": comparison.numeric_drifts,
        "incident_summary": comparison.incident_summary,
        "incident_severity": comparison.incident_severity,
    }


def save_json(payload: dict[str, Any], output_path: str | Path) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def column_to_dict(column: ColumnProfile) -> dict[str, Any]:
    return {
        "name": column.name,
        "inferred_type": column.inferred_type,
        "null_count": column.null_count,
        "null_rate": column.null_rate,
        "unique_count": column.unique_count,
        "sample_values": column.sample_values,
        "numeric_summary": (
            {
                "min_value": column.numeric_summary.min_value,
                "max_value": column.numeric_summary.max_value,
                "mean": column.numeric_summary.mean,
                "median": column.numeric_summary.median,
                "p05": column.numeric_summary.p05,
                "p95": column.numeric_summary.p95,
                "outlier_count": column.numeric_summary.outlier_count,
                "outlier_rate": column.numeric_summary.outlier_rate,
            }
            if column.numeric_summary
            else None
        ),
    }


def _profile_column(name: str, rows: list[dict[str, str | None]]) -> ColumnProfile:
    raw_values = [row.get(name) for row in rows]
    normalized_values = [_normalize_cell(value) for value in raw_values]
    non_null_values = [value for value in normalized_values if value is not None]
    inferred_type = _infer_type(non_null_values)
    sample_values = list(dict.fromkeys(non_null_values))[:3]
    unique_count = len(set(non_null_values))
    null_count = len(normalized_values) - len(non_null_values)
    null_rate = round(null_count / len(normalized_values), 3) if normalized_values else 0.0
    numeric_summary = _numeric_summary(non_null_values) if inferred_type in {"integer", "float"} else None
    return ColumnProfile(
        name=name,
        inferred_type=inferred_type,
        null_count=null_count,
        null_rate=null_rate,
        unique_count=unique_count,
        sample_values=sample_values,
        numeric_summary=numeric_summary,
    )


def _normalize_cell(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    if stripped == "" or stripped.lower() in {"null", "none", "na", "n/a"}:
        return None
    return stripped


def _infer_type(values: list[str]) -> str:
    if not values:
        return "unknown"
    if all(_is_int(value) for value in values):
        return "integer"
    if all(_is_float(value) for value in values):
        return "float"
    if all(value.lower() in {"true", "false"} for value in values):
        return "boolean"
    return "string"


def _numeric_summary(values: list[str]) -> NumericSummary:
    numbers = [float(value) for value in values]
    ordered = sorted(numbers)
    q1 = _percentile(ordered, 0.25)
    q3 = _percentile(ordered, 0.75)
    iqr = q3 - q1
    lower_fence = q1 - 1.5 * iqr
    upper_fence = q3 + 1.5 * iqr
    outlier_count = sum(1 for value in numbers if value < lower_fence or value > upper_fence)
    return NumericSummary(
        min_value=round(min(numbers), 3),
        max_value=round(max(numbers), 3),
        mean=round(sum(numbers) / len(numbers), 3),
        median=round(_percentile(ordered, 0.5), 3),
        p05=round(_percentile(ordered, 0.05), 3),
        p95=round(_percentile(ordered, 0.95), 3),
        outlier_count=outlier_count,
        outlier_rate=round(outlier_count / len(numbers), 3),
    )


def _percentile(values: list[float], fraction: float) -> float:
    if not values:
        return 0.0
    if len(values) == 1:
        return values[0]
    position = (len(values) - 1) * fraction
    lower_index = math.floor(position)
    upper_index = math.ceil(position)
    if lower_index == upper_index:
        return values[lower_index]
    lower_value = values[lower_index]
    upper_value = values[upper_index]
    return lower_value + (upper_value - lower_value) * (position - lower_index)


def _schema_fingerprint(columns: list[ColumnProfile]) -> str:
    signature = "|".join(f"{column.name}:{column.inferred_type}" for column in columns)
    return hashlib.sha256(signature.encode("utf-8")).hexdigest()[:16]


def _ratio_delta(baseline: float, candidate: float) -> float:
    if baseline == 0:
        if candidate == 0:
            return 0.0
        return 1.0
    return round((candidate - baseline) / abs(baseline), 3)


def _incident_report(
    *,
    baseline: DatasetProfile,
    candidate: DatasetProfile,
    added_columns: list[str],
    removed_columns: list[str],
    type_changes: list[dict[str, str]],
    null_rate_drifts: list[dict[str, Any]],
    numeric_drifts: list[dict[str, Any]],
) -> tuple[str, str]:
    row_delta_ratio = abs(_ratio_delta(float(baseline.row_count), float(candidate.row_count)))
    severe_nulls = [item for item in null_rate_drifts if abs(item["delta"]) >= 0.2]
    severe_numeric = [
        item for item in numeric_drifts if abs(item["mean_delta_ratio"]) >= 0.5 or abs(item["outlier_delta"]) >= 0.15
    ]

    if removed_columns or type_changes or row_delta_ratio >= 0.25:
        parts = []
        if removed_columns:
            parts.append(f"columns removed: {', '.join(removed_columns)}")
        if type_changes:
            parts.append(
                "type changes: "
                + ", ".join(f"{item['column']} ({item['baseline_type']} -> {item['candidate_type']})" for item in type_changes)
            )
        if row_delta_ratio >= 0.25:
            parts.append(f"row count moved from {baseline.row_count} to {candidate.row_count}")
        return ("Critical incident: " + "; ".join(parts) + "."), "critical"

    if added_columns or severe_nulls or severe_numeric:
        parts = []
        if added_columns:
            parts.append(f"new columns detected: {', '.join(added_columns)}")
        if severe_nulls:
            worst = severe_nulls[0]
            parts.append(
                f"null-rate drift on {worst['column']} ({worst['baseline_null_rate']:.3f} -> {worst['candidate_null_rate']:.3f})"
            )
        if severe_numeric:
            worst_numeric = severe_numeric[0]
            parts.append(
                f"numeric shift on {worst_numeric['column']} (mean delta {worst_numeric['mean_delta_ratio']:+.3f}, outlier delta {worst_numeric['outlier_delta']:+.3f})"
            )
        return ("Warning incident: " + "; ".join(parts) + "."), "warning"

    return ("Healthy profile change: no material schema or value drift detected."), "info"


def _is_int(value: str) -> bool:
    try:
        if value.startswith("+"):
            return False
        int(value)
        return "." not in value
    except ValueError:
        return False


def _is_float(value: str) -> bool:
    try:
        float(value)
        return True
    except ValueError:
        return False
