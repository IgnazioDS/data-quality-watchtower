export interface IncidentMetric {
  label: string;
  baseline: string;
  candidate: string;
  delta: string;
}

export interface IncidentDrift {
  category: "schema" | "null" | "numeric" | "cardinality";
  column: string;
  severity: "critical" | "warning";
  summary: string;
}

export const INCIDENT_METRICS: IncidentMetric[] = [
  { label: "Rows", baseline: "12", candidate: "9", delta: "-25%" },
  { label: "Schema fingerprint", baseline: "52e84b2d44953ac9", candidate: "cf171c4c74e3d910", delta: "changed" },
  { label: "Severity", baseline: "healthy", candidate: "critical", delta: "escalated" },
  { label: "Gate verdict", baseline: "pass", candidate: "fail", delta: "blocked" },
];

export const INCIDENT_DRIFTS: IncidentDrift[] = [
  {
    category: "schema",
    column: "customer_id",
    severity: "critical",
    summary: "Type changed from integer to string, which invalidates downstream joins and ID assumptions.",
  },
  {
    category: "schema",
    column: "region",
    severity: "critical",
    summary: "Column disappeared entirely in the drifted snapshot.",
  },
  {
    category: "null",
    column: "discount_pct",
    severity: "warning",
    summary: "Null rate jumped from 0.000 to 0.889, suggesting upstream extraction loss or partial writes.",
  },
  {
    category: "numeric",
    column: "revenue_usd",
    severity: "warning",
    summary: "Mean moved from 103.408 to 624.683 and outlier rate nearly tripled due to a suspicious 5400.00 spike.",
  },
  {
    category: "cardinality",
    column: "customer_id",
    severity: "critical",
    summary: "Identifier cardinality collapsed and formatting shifted, a strong signal that source semantics changed.",
  },
];

export const INCIDENT_COMMANDS = {
  baseline:
    "uv run data-quality-watchtower profile examples/orders.csv --output baseline.json",
  candidate:
    "uv run data-quality-watchtower profile examples/orders_drifted.csv --output new_run.json",
  compare:
    "uv run data-quality-watchtower compare baseline.json new_run.json --format markdown --report reports/incident.md",
  gate:
    "uv run data-quality-watchtower gate baseline.json new_run.json --allowed-severity warning --max-row-count-drop-ratio 0.15",
  inspect:
    "uv run data-quality-watchtower show baseline.json",
};

export const INCIDENT_REPORT = `# Data Quality Gate FAIL

- Allowed severity: \`warning\`
- Max row-count drop ratio: \`0.150\`
- Max null drift count: \`0\`
- Max numeric drift count: \`0\`
- Max cardinality drift count: \`0\`

## Reasons

- incident severity critical exceeded allowed warning
- row-count drop 0.250 exceeded limit 0.150
- null-rate drift count 1 exceeded limit 0
- numeric drift count 3 exceeded limit 0
- cardinality drift count 1 exceeded limit 0`;
