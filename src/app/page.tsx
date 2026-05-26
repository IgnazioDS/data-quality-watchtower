"use client";

import { useEffect, useState } from "react";
import {
  AlertTriangle,
  ArrowRight,
  Database,
  ExternalLink,
  Github,
  Layers,
  ListChecks,
  Users,
} from "lucide-react";
import {
  fetchIncidentLatest,
  fetchPublicStats,
  type IncidentLatest,
  type PublicStats,
} from "@/lib/api";
import { TopBar } from "@/components/layout/TopBar";
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { StatusDot } from "@/components/ui/status-dot";
import { StatCard } from "@/components/dashboard/StatCard";
import { IncidentHero } from "@/components/dashboard/IncidentHero";
import { VerdictHistory } from "@/components/dashboard/VerdictHistory";
import { PROJECT } from "@/lib/project";
import { formatRelative } from "@/lib/utils";

export default function OverviewPage() {
  const [stats, setStats] = useState<PublicStats | null>(null);
  const [incident, setIncident] = useState<IncidentLatest | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      fetchPublicStats().catch(() => null),
      fetchIncidentLatest().catch(() => null),
    ])
      .then(([s, i]) => {
        setStats(s);
        setIncident(i);
      })
      .finally(() => setLoading(false));
  }, []);

  const metrics = stats?.metrics;
  const datasets = (metrics?.datasets_monitored as number | undefined) ?? 0;
  const checks24h = (metrics?.checks_run_24h as number | undefined) ?? 0;
  const anomalies24h = (metrics?.anomalies_detected_24h as number | undefined) ?? 0;
  const schemaDrifts30d = (metrics?.schema_drifts_30d as number | undefined) ?? 0;
  const uptime = stats?.uptime_pct_30d;

  return (
    <>
      <TopBar
        title={PROJECT.name}
        description={PROJECT.summary}
        actions={
          <Button asChild size="sm" variant="outline">
            <a href="/telemetry">
              Open telemetry
              <ExternalLink />
            </a>
          </Button>
        }
      />
      <div className="dot-grid grid-fade flex-1 overflow-y-auto">
        <div className="page-enter mx-auto max-w-6xl space-y-5 p-6">
          {/* Pitch banner */}
          <Card className="overflow-hidden">
            <CardContent className="grid gap-4 p-6 lg:grid-cols-[1fr,auto] lg:items-center">
              <div className="space-y-3 max-w-2xl">
                <div className="flex flex-wrap items-center gap-1.5">
                  <Badge variant="brand">{PROJECT.stage}</Badge>
                  <Badge variant="outline">{PROJECT.category}</Badge>
                  <Badge variant="outline">{PROJECT.track}</Badge>
                </div>
                <h2 className="text-2xl font-semibold tracking-tight text-foreground">
                  {PROJECT.summary}
                </h2>
                <p className="text-sm text-foreground-muted leading-relaxed">
                  <span className="text-foreground">Problem.</span> {PROJECT.problem}{" "}
                  <span className="text-foreground">Why now.</span> {PROJECT.why_now}
                </p>
              </div>
              <div className="flex flex-row gap-2 lg:flex-col">
                <Button asChild size="sm" variant="primary">
                  <a href="/prototype">
                    View prototype incident
                    <ArrowRight />
                  </a>
                </Button>
                <Button asChild size="sm" variant="outline">
                  <a href="/capabilities">
                    See capabilities
                    <ArrowRight />
                  </a>
                </Button>
                <Button asChild size="sm" variant="outline">
                  <a href={PROJECT.github_url} target="_blank" rel="noreferrer">
                    <Github />
                    GitHub
                  </a>
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* Latest incident from the nightly drift scan */}
          <IncidentHero incident={incident} loading={loading} />

          {/* Tier-A workload counters, wired to the real /api/stats */}
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <StatCard
              title="Datasets monitored"
              value={datasets}
              subtitle="Synthetic fixtures"
              icon={Database}
              loading={loading}
            />
            <StatCard
              title="Checks · 24h"
              value={checks24h}
              subtitle="Trailing 24 hours"
              icon={ListChecks}
              loading={loading}
            />
            <StatCard
              title="Anomalies · 24h"
              value={anomalies24h}
              subtitle="Drift findings"
              icon={AlertTriangle}
              loading={loading}
            />
            <StatCard
              title="Schema drifts · 30d"
              value={schemaDrifts30d}
              subtitle="Trailing 30 days"
              icon={Layers}
              loading={loading}
            />
          </div>

          {/* 30-day verdict history */}
          <VerdictHistory runs={incident?.recent_runs} />

          {/* Status row */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between border-b border-border-subtle py-3">
              <CardTitle>System status</CardTitle>
              <Badge variant={stats?.status === "operational" ? "success" : "warning"}>
                <StatusDot
                  tone={stats?.status === "operational" ? "success" : "warning"}
                  pulse={stats?.status === "operational"}
                  size="sm"
                />
                {stats?.status ?? "unknown"}
              </Badge>
            </CardHeader>
            <CardContent className="grid grid-cols-2 gap-4 py-4 sm:grid-cols-4">
              <StatusCell label="Mode" value={stats?.mode ?? "live"} hint="Tier A workload" />
              <StatusCell
                label="Last check"
                value={formatRelative(metrics?.last_check_at as string | undefined)}
                hint="nightly drift scan"
              />
              <StatusCell
                label="Uptime · 30d"
                value={uptime === undefined ? "—" : `${uptime}%`}
                hint="scan cadence"
              />
              <StatusCell
                label="Schema"
                value={`v${stats?.schema_version ?? 1}`}
                hint="public contract"
              />
            </CardContent>
          </Card>

          {/* Built for + what the engine does */}
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
            <Card className="lg:col-span-1">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Users className="h-3.5 w-3.5 text-brand" />
                  Built for
                </CardTitle>
                <CardDescription>{PROJECT.users}</CardDescription>
              </CardHeader>
              <CardContent>
                <p className="text-2xs font-medium uppercase tracking-wider text-foreground-faint mb-2">
                  Engine
                </p>
                <div className="flex flex-wrap gap-1.5">
                  {PROJECT.stack.map((s) => (
                    <Badge key={s} variant="muted">
                      {s}
                    </Badge>
                  ))}
                </div>
              </CardContent>
            </Card>
            <Card className="lg:col-span-2">
              <CardHeader>
                <CardTitle>What the engine does</CardTitle>
                <CardDescription>
                  The capabilities running in the nightly drift scan.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <ul className="space-y-2.5">
                  {PROJECT.mvp.map((item, i) => (
                    <li
                      key={i}
                      className="flex items-start gap-3 text-sm text-foreground-muted"
                    >
                      <span className="mt-1.5 inline-flex h-1.5 w-1.5 shrink-0 rounded-full bg-brand" />
                      {item}
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </>
  );
}

function StatusCell({
  label,
  value,
  hint,
}: {
  label: string;
  value: string;
  hint?: string;
}) {
  return (
    <div>
      <p className="text-2xs font-medium uppercase tracking-wider text-foreground-faint">
        {label}
      </p>
      <p className="mt-1 text-xl font-semibold tabular-nums text-foreground">
        {value}
      </p>
      {hint && (
        <p className="mt-0.5 text-2xs text-foreground-subtle truncate">{hint}</p>
      )}
    </div>
  );
}
