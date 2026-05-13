from __future__ import annotations

import argparse
import json
from pathlib import Path

from .catalog import load_project
from .watchtower import (
    compare_profiles,
    comparison_to_dict,
    format_comparison,
    format_profile,
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
    profile_parser.add_argument("--format", choices=("text", "json"), default="text", help="Output format.")

    compare_parser = subparsers.add_parser("compare", help="Compare two saved profile JSON files.")
    compare_parser.add_argument("baseline", help="Path to the baseline profile JSON.")
    compare_parser.add_argument("candidate", help="Path to the candidate profile JSON.")
    compare_parser.add_argument("--report", help="Optional path for saved comparison JSON or markdown-style text.")
    compare_parser.add_argument("--format", choices=("text", "json"), default="text", help="Output format.")
    return parser


def run(argv: list[str] | None = None) -> str:
    args = build_parser().parse_args(argv)
    project = load_project()

    if args.command == "summary":
        return "\n".join([
            project.name,
            "=" * len(project.name),
            project.summary,
            "",
            f"Problem: {project.problem}",
            f"Users: {project.users}",
            f"Stage: {project.stage}",
            f"Track: {project.track}",
        ])
    if args.command == "capabilities":
        lines = [project.name, "", "Core capabilities:"]
        lines.extend(f"- {item}" for item in project.mvp)
        return "\n".join(lines)
    if args.command == "roadmap":
        roadmap_path = Path(__file__).resolve().parents[2] / "docs" / "roadmap.md"
        return roadmap_path.read_text(encoding="utf-8").strip()
    if args.command == "profile":
        profile = profile_dataset(args.dataset)
        payload = profile_to_dict(profile)
        if args.output:
            save_json(payload, args.output)
        if args.format == "json":
            return json.dumps(payload, indent=2)
        output = format_profile(profile)
        if args.output:
            output += f"\nSaved profile: {args.output}"
        return output
    if args.command == "compare":
        comparison = compare_profiles(args.baseline, args.candidate)
        payload = comparison_to_dict(comparison)
        if args.report:
            if args.format == "json":
                save_json(payload, args.report)
            else:
                report_path = Path(args.report)
                report_path.parent.mkdir(parents=True, exist_ok=True)
                report_path.write_text(format_comparison(comparison) + "\n", encoding="utf-8")
        if args.format == "json":
            return json.dumps(payload, indent=2)
        output = format_comparison(comparison)
        if args.report:
            output += f"\nSaved report: {args.report}"
        return output
    raise ValueError(f"Unsupported command: {args.command}")


def main(argv: list[str] | None = None) -> int:
    print(run(argv))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
