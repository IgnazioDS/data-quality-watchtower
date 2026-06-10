// Slim API surface for the public dashboard.
// Two real, public, unauthenticated endpoints back this UI:
//   GET /api/stats            Tier-A live telemetry (see TELEMETRY_SCHEMA.md)
//   GET /api/incident-latest  the latest committed drift-scan incident
// Both read repo-committed JSON artifacts the nightly cron produces.

async function publicFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
  });
  if (!res.ok) {
    throw new Error(`Public API ${res.status}: ${res.statusText}`);
  }
  return res.json() as Promise<T>;
}

/** Tier-A live telemetry response. See TELEMETRY_SCHEMA.md. */
export interface PublicStats {
  system: string;
  mode?: "live" | "showcase";
  status: "operational" | "degraded" | "down";
  last_deployed_at: string | null;
  last_active_at?: string | null;
  uptime_pct_30d?: number;
  metrics: {
    // Tier-A (live) shape for data-quality-watchtower.
    datasets_monitored?: number;
    checks_run_24h?: number;
    anomalies_detected_24h?: number;
    schema_drifts_30d?: number;
    last_check_at?: string | null;
    // Tier-B (showcase/degraded fallback) fields stay optional.
    commits_30d?: number;
    commits_total?: number;
    primary_language?: string;
    repo_stars?: number;
    lines_of_code?: number;
    [key: string]: number | string | null | undefined;
  };
  schema_version: number;
  generated_at: string;
}

export type Severity = "info" | "warning" | "critical";
export type Verdict = "pass" | "fail" | "unknown";

export interface IncidentFinding {
  kind: string;
  column: string;
  severity: Severity;
  message: string;
  detail?: Record<string, string>;
}

export interface RecentRun {
  date: string;
  severity: Severity;
  gate_verdict: Verdict;
  drift_detected: boolean;
  anomalies_detected: number;
}

export interface PreviousRun {
  run_id: string | null;
  generated_at: string | null;
  scenario: string | null;
  severity: Severity;
  gate_verdict: Verdict;
  drift_detected: boolean;
  delta?: Record<string, string>;
}

/** Latest drift-scan incident. See /api/incident-latest. */
export interface IncidentLatest {
  system: string;
  benchmark_type?: "drift";
  schema_version: number;
  status?: "operational" | "degraded";
  run_id: string | null;
  fixture: string | null;
  scenario: string | null;
  scenario_title?: string;
  scenario_description?: string;
  baseline_rows?: number;
  current_rows?: number;
  drift_detected: boolean;
  severity: Severity;
  gate_verdict: Verdict;
  detection_reasons: string[];
  findings?: IncidentFinding[];
  datasets_monitored?: number;
  metrics?: {
    checks_run?: number;
    anomalies_detected?: number;
    schema_drift_count?: number;
  };
  report_url: string | null;
  generated_at: string;
  previous_run: PreviousRun | null;
  recent_runs?: RecentRun[];
}

export function fetchPublicStats(): Promise<PublicStats> {
  return publicFetch<PublicStats>("/api/stats");
}

export function fetchIncidentLatest(): Promise<IncidentLatest> {
  return publicFetch<IncidentLatest>("/api/incident-latest");
}
