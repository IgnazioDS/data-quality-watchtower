from __future__ import annotations

import argparse
import json
from pathlib import Path

from .catalog import load_project
from .watchtower import (
    GateResult,
    ProfileComparison,
    assess_gate,
    compare_profiles,
    comparison_to_dict,
    format_comparison,
    format_comparison_markdown,
    format_gate_result,
    format_profile,
    format_profile_markdown,
    gate_result_to_dict,
    load_profile,
    profile_dataset,
    profile_to_dict,
    save_json,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="data-quality-watchtower", description="Operate Data Quality Watchtower.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("summary", help="Print product summary.")
    subparsers.add_parser("capabilities", help="Print initial capabilities.")
    subparsers.add_parser("roadmap", help="Print roadmap.")

    profile_parser = subparsers.add_parser("profile", help="Profile a CSV dataset.")
    profile_parser.add_argument("dataset", help="Path to a CSV dataset.")
    profile_parser.add_argument("--output", help="Optional path for saved profile JSON.")
    profile_parser.add_argument("--format", choices=("text", "json", "markdown"), default="text", help="Output format.")

    show_parser = subparsers.add_parser("show", help="Inspect a saved profile JSON file.")
    show_parser.add_argument("profile", help="Path to a saved profile JSON file.")
    show_parser.add_argument("--format", choices=("text", "json", "markdown"), default="text", help="Output format.")

    compare_parser = subparsers.add_parser("compare", help="Compare two saved profile JSON files.")
    compare_parser.add_argument("baseline", help="Path to the baseline profile JSON.")
    compare_parser.add_argument("candidate", help="Path to the candidate profile JSON.")
    compare_parser.add_argument("--report", help="Optional path for saved comparison report.")
    compare_parser.add_argument("--format", choices=("text", "json", "markdown"), default="text", help="Output format.")
    compare_parser.add_argument("--limit", type=int, default=10, help="Maximum drift rows to print.")

    gate_parser = subparsers.add_parser("gate", help="Enforce quality thresholds for CI or deploy gates.")
    gate_parser.add_argument("baseline", help="Path to the baseline profile JSON.")
    gate_parser.add_argument("candidate", help="Path to the candidate profile JSON.")
    gate_parser.add_argument("--allowed-severity", choices=("info", "warning", "critical"), default="warning")
    gate_parser.add_argument("--max-row-count-drop-ratio", type=float, default=0.15)
    gate_parser.add_argument("--max-null-drift-count", type=int, default=0)
    gate_parser.add_argument("--max-numeric-drift-count", type=int, default=0)
    gate_parser.add_argument("--max-cardinality-drift-count", type=int, default=0)
    gate_parser.add_argument("--report", help="Optional path for saved gate report.")
    gate_parser.add_argument("--format", choices=("text", "json", "markdown"), default="text", help="Output format.")
    gate_parser.add_argument("--limit", type=int, default=10, help="Maximum drift rows to print.")
    return parser


def execute(argv: list[str] | None = None) -> tuple[str, int]:
    args = build_parser().parse_args(argv)
    project = load_project()

    if args.command == "summary":
        return (
            "\n".join([
                project.name,
                "=" * len(project.name),
                project.summary,
                "",
                f"Problem: {project.problem}",
                f"Users: {project.users}",
                f"Stage: {project.stage}",
                f"Track: {project.track}",
            ]),
            0,
        )
    if args.command == "capabilities":
        lines = [project.name, "", "Core capabilities:"]
        lines.extend(f"- {item}" for item in project.mvp)
        return "\n".join(lines), 0
    if args.command == "roadmap":
        roadmap_path = Path(__file__).resolve().parents[2] / "docs" / "roadmap.md"
        return roadmap_path.read_text(encoding="utf-8").strip(), 0
    if args.command == "profile":
        profile = profile_dataset(args.dataset)
        payload = profile_to_dict(profile)
        if args.output:
            save_json(payload, args.output)
        if args.format == "json":
            return json.dumps(payload, indent=2), 0
        if args.format == "markdown":
            output = format_profile_markdown(profile)
        else:
            output = format_profile(profile)
        if args.output:
            output += f"\nSaved profile: {args.output}"
        return output, 0
    if args.command == "show":
        profile = load_profile(args.profile)
        if args.format == "json":
            return json.dumps(profile_to_dict(profile), indent=2), 0
        if args.format == "markdown":
            return format_profile_markdown(profile), 0
        return format_profile(profile), 0
    if args.command == "compare":
        comparison = compare_profiles(args.baseline, args.candidate)
        output = _render_comparison(comparison, output_format=args.format, limit=args.limit)
        _write_report_if_requested(args.report, output)
        return output, 0
    if args.command == "gate":
        comparison = compare_profiles(args.baseline, args.candidate)
        gate = assess_gate(
            comparison,
            allowed_severity=args.allowed_severity,
            max_row_count_drop_ratio=args.max_row_count_drop_ratio,
            max_null_drift_count=args.max_null_drift_count,
            max_numeric_drift_count=args.max_numeric_drift_count,
            max_cardinality_drift_count=args.max_cardinality_drift_count,
        )
        if args.format == "json":
            output = json.dumps(gate_result_to_dict(gate), indent=2)
        elif args.format == "markdown":
            output = _render_gate_markdown(gate, limit=args.limit)
        else:
            output = format_gate_result(gate, limit=args.limit)
        _write_report_if_requested(args.report, output)
        return output, 0 if gate.passed else 2
    raise ValueError(f"Unsupported command: {args.command}")


def run(argv: list[str] | None = None) -> str:
    return execute(argv)[0]


def main(argv: list[str] | None = None) -> int:
    output, exit_code = execute(argv)
    print(output)
    return exit_code


def _render_comparison(comparison: ProfileComparison, *, output_format: str, limit: int) -> str:
    if output_format == "json":
        return json.dumps(comparison_to_dict(comparison), indent=2)
    if output_format == "markdown":
        return format_comparison_markdown(comparison, limit=limit)
    return format_comparison(comparison, limit=limit)


def _render_gate_markdown(gate: GateResult, *, limit: int) -> str:
    verdict = "PASS" if gate.passed else "FAIL"
    lines = [
        f"# Data Quality Gate {verdict}",
        "",
        f"- Allowed severity: `{gate.allowed_severity}`",
        f"- Max row-count drop ratio: `{gate.max_row_count_drop_ratio:.3f}`",
        f"- Max null drift count: `{gate.max_null_drift_count}`",
        f"- Max numeric drift count: `{gate.max_numeric_drift_count}`",
        f"- Max cardinality drift count: `{gate.max_cardinality_drift_count}`",
        "",
    ]
    if gate.reasons:
        lines.append("## Reasons")
        lines.append("")
        lines.extend(f"- {reason}" for reason in gate.reasons)
        lines.append("")
    lines.append(format_comparison_markdown(gate.comparison, limit=limit))
    return "\n".join(lines)


def _write_report_if_requested(report_path: str | None, output: str) -> None:
    if not report_path:
        return
    path = Path(report_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(output + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
