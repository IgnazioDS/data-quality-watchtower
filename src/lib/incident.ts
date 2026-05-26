// Presentation helpers for the latest-incident surfaces. Pure functions so
// the mapping from drift severity to UI tone stays testable and in one place.
// Severity vocabulary matches the engine in watchtower.py: info, warning, critical.
import type { RecentRun, Severity, Verdict } from "./api";

/** Numeric score per severity, used for the verdict-history sparkline. */
export const SEVERITY_SCORE: Record<Severity, number> = {
  info: 0,
  warning: 1,
  critical: 2,
};

export type Tone = "success" | "info" | "warning" | "danger" | "muted";

/** Map a drift severity to a semantic UI tone. */
export function severityTone(severity: Severity): Tone {
  switch (severity) {
    case "info":
      return "success";
    case "warning":
      return "warning";
    case "critical":
      return "danger";
    default:
      return "muted";
  }
}

/** Map a gate verdict to a semantic UI tone. */
export function verdictTone(verdict: Verdict): Tone {
  if (verdict === "pass") return "success";
  if (verdict === "fail") return "danger";
  return "muted";
}

/**
 * Chronological severity series for the sparkline. `recent_runs` arrives
 * newest-first, so it is reversed to read left-to-right oldest-to-newest.
 */
export function severitySeries(runs: RecentRun[] | undefined): number[] {
  if (!runs || runs.length === 0) return [];
  return [...runs].reverse().map((run) => SEVERITY_SCORE[run.severity] ?? 0);
}

/** Human label for a scenario key when the artifact lacks a title. */
export function scenarioLabel(key: string | null | undefined): string {
  if (!key) return "—";
  return key
    .split("_")
    .map((word) => (word ? word[0].toUpperCase() + word.slice(1) : word))
    .join(" ");
}
