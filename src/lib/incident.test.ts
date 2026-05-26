import { describe, expect, it } from "vitest";
import {
  SEVERITY_SCORE,
  scenarioLabel,
  severitySeries,
  severityTone,
  verdictTone,
} from "./incident";
import type { RecentRun } from "./api";

describe("severityTone", () => {
  it("maps severities to tones", () => {
    expect(severityTone("info")).toBe("success");
    expect(severityTone("warning")).toBe("warning");
    expect(severityTone("critical")).toBe("danger");
  });
});

describe("verdictTone", () => {
  it("maps verdicts to tones", () => {
    expect(verdictTone("pass")).toBe("success");
    expect(verdictTone("fail")).toBe("danger");
    expect(verdictTone("unknown")).toBe("muted");
  });
});

describe("severitySeries", () => {
  it("returns empty for no runs", () => {
    expect(severitySeries(undefined)).toEqual([]);
    expect(severitySeries([])).toEqual([]);
  });

  it("reverses newest-first runs into chronological scores", () => {
    const runs: RecentRun[] = [
      { date: "2026-05-26", severity: "critical", gate_verdict: "fail", drift_detected: true, anomalies_detected: 1 },
      { date: "2026-05-25", severity: "warning", gate_verdict: "fail", drift_detected: true, anomalies_detected: 1 },
    ];
    expect(severitySeries(runs)).toEqual([
      SEVERITY_SCORE.warning,
      SEVERITY_SCORE.critical,
    ]);
  });
});

describe("scenarioLabel", () => {
  it("humanises a scenario key", () => {
    expect(scenarioLabel("value_distribution_shift")).toBe("Value Distribution Shift");
  });

  it("handles null", () => {
    expect(scenarioLabel(null)).toBe("—");
  });
});
