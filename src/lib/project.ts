/**
 * Project metadata sourced from `src/data_quality_watchtower/project.json`.
 * Hardcoded as a TS module so it ships in the static bundle without runtime
 * file-system access.
 */

export interface ProjectSpec {
  slug: string;
  name: string;
  category: string;
  track: string;
  stage: string;
  summary: string;
  problem: string;
  users: string;
  stack: string[];
  why_now: string;
  mvp: string[];
  github_url: string;
  /** Slug returned by the system's `/api/stats` endpoint. */
  system_slug: string;
}

export const PROJECT: ProjectSpec = {
  slug: "data-quality-watchtower",
  name: "Data Quality Watchtower",
  category: "Data Tool",
  track: "ML",
  stage: "Prototype",
  summary:
    "A monitoring assistant that detects schema drift, anomalies, and suspicious dataset changes before pipelines break.",
  problem:
    "Data issues usually surface downstream after dashboards, models, or reports are already wrong.",
  users: "Data teams, analytics engineers, ML ops teams",
  stack: ["Python", "DuckDB", "Great Expectations", "Pandas"],
  why_now:
    "Data quality remains operationally important even for AI-native products.",
  mvp: [
    "Profile tabular datasets and schemas",
    "Detect drift and row-level anomalies",
    "Generate plain-language incident summaries",
    "Store historical validation results",
    "Compare saved profiles for schema, null-rate, and outlier drift",
  ],
  github_url: "https://github.com/IgnazioDS/data-quality-watchtower",
  system_slug: "data-quality-watchtower",
};
