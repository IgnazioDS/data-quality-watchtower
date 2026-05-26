"use client";

import { AlertTriangle, CheckCircle2, FileText } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { StatusDot } from "@/components/ui/status-dot";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import type { IncidentLatest } from "@/lib/api";
import { scenarioLabel, severityTone, verdictTone } from "@/lib/incident";
import { formatRelative } from "@/lib/utils";

/**
 * Latest-incident hero. Renders the most recent committed drift scan: scenario,
 * severity, gate verdict, the plain-language reasons, the run-over-run delta,
 * and a link to the full report. The data is the artifact the nightly cron
 * committed, served by /api/incident-latest.
 */
export function IncidentHero({
  incident,
  loading,
}: {
  incident: IncidentLatest | null;
  loading: boolean;
}) {
  if (loading || !incident) {
    return (
      <Card>
        <CardContent className="space-y-3 p-6">
          <Skeleton className="h-5 w-48" />
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-3/4" />
        </CardContent>
      </Card>
    );
  }

  const failing = incident.gate_verdict === "fail";
  const sevTone = severityTone(incident.severity);
  const verTone = verdictTone(incident.gate_verdict);
  const title = incident.scenario_title ?? scenarioLabel(incident.scenario);
  const reasons = incident.detection_reasons ?? [];
  const prev = incident.previous_run;

  return (
    <Card className="overflow-hidden">
      <CardContent className="space-y-4 p-6">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div className="flex items-start gap-3">
            <div
              className={`mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-md ${
                failing
                  ? "bg-danger/10 text-danger"
                  : "bg-success/10 text-success"
              }`}
            >
              {failing ? (
                <AlertTriangle className="h-4 w-4" strokeWidth={2} />
              ) : (
                <CheckCircle2 className="h-4 w-4" strokeWidth={2} />
              )}
            </div>
            <div>
              <p className="text-2xs font-medium uppercase tracking-wider text-foreground-faint">
                Latest drift scan
              </p>
              <h3 className="text-lg font-semibold tracking-tight text-foreground">
                {title}
              </h3>
              <p className="mt-0.5 text-2xs text-foreground-subtle">
                {formatRelative(incident.generated_at)} · fixture{" "}
                <span className="font-mono">{incident.fixture ?? "—"}</span>
              </p>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-1.5">
            <Badge variant={sevTone}>
              <StatusDot tone={sevTone} size="sm" />
              {incident.severity}
            </Badge>
            <Badge variant={verTone}>{incident.gate_verdict}</Badge>
          </div>
        </div>

        <div className="rounded-md border border-border-subtle bg-surface-2 p-4">
          <p className="text-2xs font-medium uppercase tracking-wider text-foreground-faint">
            What the scan found
          </p>
          {reasons.length > 0 ? (
            <ul className="mt-2 space-y-2">
              {reasons.map((reason, i) => (
                <li
                  key={i}
                  className="flex items-start gap-2 text-sm leading-relaxed text-foreground-muted"
                >
                  <span
                    className={`mt-1.5 inline-flex h-1.5 w-1.5 shrink-0 rounded-full ${
                      failing ? "bg-danger" : "bg-warning"
                    }`}
                  />
                  {reason}
                </li>
              ))}
            </ul>
          ) : (
            <p className="mt-2 text-sm text-foreground-muted">
              No drift above thresholds. The current dataset matches the baseline
              contract.
            </p>
          )}
        </div>

        {prev && prev.delta && (
          <p className="text-2xs text-foreground-subtle">
            Since the previous scan:{" "}
            <span className="font-mono text-foreground-muted">
              severity {prev.delta.severity}
            </span>{" "}
            ·{" "}
            <span className="font-mono text-foreground-muted">
              verdict {prev.delta.gate_verdict}
            </span>
          </p>
        )}

        {incident.report_url && (
          <Button asChild size="sm" variant="outline">
            <a href={incident.report_url} target="_blank" rel="noreferrer">
              <FileText />
              Read the full incident report
            </a>
          </Button>
        )}
      </CardContent>
    </Card>
  );
}
