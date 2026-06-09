import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import {
  fetchPublicStats,
  fetchIncidentLatest,
  type PublicStats,
  type IncidentLatest,
} from "./api";

describe("api", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  describe("fetchPublicStats", () => {
    it("fetches and parses /api/stats successfully", async () => {
      const mockData: PublicStats = {
        system: "data-quality-watchtower",
        mode: "live",
        status: "operational",
        last_deployed_at: "2026-05-26T00:00:00Z",
        last_active_at: "2026-05-26T12:00:00Z",
        uptime_pct_30d: 99.5,
        metrics: {
          datasets_monitored: 42,
          checks_run_24h: 120,
          anomalies_detected_24h: 3,
          schema_drifts_30d: 1,
          last_check_at: "2026-05-26T12:30:00Z",
        },
        schema_version: 1,
        generated_at: "2026-05-26T12:30:00Z",
      };

      const mockResponse = new Response(JSON.stringify(mockData), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });

      vi.mocked(fetch).mockResolvedValueOnce(mockResponse);

      const result = await fetchPublicStats();
      expect(result).toEqual(mockData);
      expect(fetch).toHaveBeenCalledWith("/api/stats", {
        headers: { "Content-Type": "application/json" },
      });
    });

    it("throws on non-ok status", async () => {
      const mockResponse = new Response("Not Found", {
        status: 404,
        statusText: "Not Found",
      });

      vi.mocked(fetch).mockResolvedValueOnce(mockResponse);

      await expect(fetchPublicStats()).rejects.toThrow("Public API 404: Not Found");
    });

    it("propagates fetch network errors", async () => {
      const error = new Error("Network unreachable");
      vi.mocked(fetch).mockRejectedValueOnce(error);

      await expect(fetchPublicStats()).rejects.toBe(error);
    });

    it("handles 500 server error", async () => {
      const mockResponse = new Response("Internal Server Error", {
        status: 500,
        statusText: "Internal Server Error",
      });

      vi.mocked(fetch).mockResolvedValueOnce(mockResponse);

      await expect(fetchPublicStats()).rejects.toThrow("Public API 500: Internal Server Error");
    });
  });

  describe("fetchIncidentLatest", () => {
    it("fetches and parses /api/incident-latest successfully", async () => {
      const mockData: IncidentLatest = {
        system: "data-quality-watchtower",
        schema_version: 1,
        benchmark_type: "drift",
        status: "operational",
        run_id: "dqw-2026-05-26-value_distribution_shift",
        fixture: "orders",
        scenario: "value_distribution_shift",
        scenario_title: "Value Distribution Shift",
        scenario_description: "Detects when column distributions shift unexpectedly",
        baseline_rows: 12,
        current_rows: 9,
        drift_detected: true,
        severity: "critical",
        gate_verdict: "fail",
        detection_reasons: ["Column revenue_usd mean shifted significantly"],
        findings: [],
        datasets_monitored: 5,
        metrics: {
          checks_run: 150,
          anomalies_detected: 2,
          schema_drift_count: 1,
        },
        report_url: "https://github.com/IgnazioDS/data-quality-watchtower/reports/incident.md",
        generated_at: "2026-05-26T06:00:00Z",
        previous_run: null,
        recent_runs: [
          {
            date: "2026-05-25",
            severity: "info",
            gate_verdict: "pass",
            drift_detected: false,
            anomalies_detected: 0,
          },
        ],
      };

      const mockResponse = new Response(JSON.stringify(mockData), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });

      vi.mocked(fetch).mockResolvedValueOnce(mockResponse);

      const result = await fetchIncidentLatest();
      expect(result).toEqual(mockData);
      expect(fetch).toHaveBeenCalledWith("/api/incident-latest", {
        headers: { "Content-Type": "application/json" },
      });
    });

    it("throws on non-ok status", async () => {
      const mockResponse = new Response("Service Unavailable", {
        status: 503,
        statusText: "Service Unavailable",
      });

      vi.mocked(fetch).mockResolvedValueOnce(mockResponse);

      await expect(fetchIncidentLatest()).rejects.toThrow(
        "Public API 503: Service Unavailable"
      );
    });

    it("propagates fetch network errors", async () => {
      const error = new Error("Connection timeout");
      vi.mocked(fetch).mockRejectedValueOnce(error);

      await expect(fetchIncidentLatest()).rejects.toBe(error);
    });

    it("handles degraded status", async () => {
      const mockData: IncidentLatest = {
        system: "data-quality-watchtower",
        schema_version: 1,
        benchmark_type: "drift",
        status: "degraded",
        run_id: null,
        fixture: null,
        scenario: null,
        drift_detected: false,
        severity: "info",
        gate_verdict: "unknown",
        detection_reasons: [],
        findings: [],
        report_url: null,
        generated_at: "2026-05-26T12:00:00Z",
        previous_run: null,
      };

      const mockResponse = new Response(JSON.stringify(mockData), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });

      vi.mocked(fetch).mockResolvedValueOnce(mockResponse);

      const result = await fetchIncidentLatest();
      expect(result.status).toBe("degraded");
      expect(result.drift_detected).toBe(false);
    });
  });
});
