import { describe, expect, it } from "vitest";
import {
  INCIDENT_METRICS,
  INCIDENT_DRIFTS,
  INCIDENT_COMMANDS,
  INCIDENT_REPORT,
  type IncidentMetric,
  type IncidentDrift,
} from "./prototype";

describe("INCIDENT_METRICS", () => {
  it("is a non-empty array", () => {
    expect(Array.isArray(INCIDENT_METRICS)).toBe(true);
    expect(INCIDENT_METRICS.length).toBeGreaterThan(0);
  });

  it("has well-formed metric objects", () => {
    INCIDENT_METRICS.forEach((metric: IncidentMetric) => {
      expect(typeof metric.label).toBe("string");
      expect(metric.label.length).toBeGreaterThan(0);

      expect(typeof metric.baseline).toBe("string");
      expect(metric.baseline.length).toBeGreaterThan(0);

      expect(typeof metric.candidate).toBe("string");
      expect(metric.candidate.length).toBeGreaterThan(0);

      expect(typeof metric.delta).toBe("string");
      expect(metric.delta.length).toBeGreaterThan(0);
    });
  });

  it("contains expected metric labels", () => {
    const labels = INCIDENT_METRICS.map((m) => m.label);
    expect(labels).toContain("Rows");
    expect(labels).toContain("Schema fingerprint");
    expect(labels).toContain("Severity");
    expect(labels).toContain("Gate verdict");
  });
});

describe("INCIDENT_DRIFTS", () => {
  it("is a non-empty array", () => {
    expect(Array.isArray(INCIDENT_DRIFTS)).toBe(true);
    expect(INCIDENT_DRIFTS.length).toBeGreaterThan(0);
  });

  it("has well-formed drift objects", () => {
    INCIDENT_DRIFTS.forEach((drift: IncidentDrift) => {
      expect(["schema", "null", "numeric", "cardinality"]).toContain(drift.category);
      expect(typeof drift.column).toBe("string");
      expect(drift.column.length).toBeGreaterThan(0);

      expect(["critical", "warning"]).toContain(drift.severity);

      expect(typeof drift.summary).toBe("string");
      expect(drift.summary.length).toBeGreaterThan(0);
    });
  });

  it("contains expected drift categories", () => {
    const categories = INCIDENT_DRIFTS.map((d) => d.category);
    expect(categories).toContain("schema");
    expect(categories).toContain("null");
    expect(categories).toContain("numeric");
    expect(categories).toContain("cardinality");
  });

  it("contains drifts with both severity levels", () => {
    const severities = new Set(INCIDENT_DRIFTS.map((d) => d.severity));
    expect(severities.has("critical")).toBe(true);
    expect(severities.has("warning")).toBe(true);
  });
});

describe("INCIDENT_COMMANDS", () => {
  it("has all required command keys", () => {
    expect(INCIDENT_COMMANDS).toHaveProperty("baseline");
    expect(INCIDENT_COMMANDS).toHaveProperty("candidate");
    expect(INCIDENT_COMMANDS).toHaveProperty("compare");
    expect(INCIDENT_COMMANDS).toHaveProperty("gate");
    expect(INCIDENT_COMMANDS).toHaveProperty("inspect");
  });

  it("all commands are non-empty strings", () => {
    Object.values(INCIDENT_COMMANDS).forEach((cmd) => {
      expect(typeof cmd).toBe("string");
      expect(cmd.length).toBeGreaterThan(0);
    });
  });

  it("commands reference data-quality-watchtower tool", () => {
    Object.values(INCIDENT_COMMANDS).forEach((cmd) => {
      expect(cmd).toMatch(/data-quality-watchtower/);
    });
  });

  it("has realistic command patterns", () => {
    expect(INCIDENT_COMMANDS.baseline).toMatch(/uv run/);
    expect(INCIDENT_COMMANDS.baseline).toMatch(/profile/);
    expect(INCIDENT_COMMANDS.compare).toMatch(/compare/);
    expect(INCIDENT_COMMANDS.gate).toMatch(/gate/);
  });
});

describe("INCIDENT_REPORT", () => {
  it("is a non-empty string", () => {
    expect(typeof INCIDENT_REPORT).toBe("string");
    expect(INCIDENT_REPORT.length).toBeGreaterThan(0);
  });

  it("contains report header", () => {
    expect(INCIDENT_REPORT).toContain("Data Quality Gate FAIL");
  });

  it("contains configuration constraints", () => {
    expect(INCIDENT_REPORT).toContain("Allowed severity");
    expect(INCIDENT_REPORT).toContain("Max row-count drop ratio");
  });

  it("contains reasons section", () => {
    expect(INCIDENT_REPORT).toContain("Reasons");
  });

  it("references policy violations", () => {
    expect(INCIDENT_REPORT).toContain("exceeded");
  });
});
