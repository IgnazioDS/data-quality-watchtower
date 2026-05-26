"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Sparkline } from "@/components/ui/sparkline";
import { Badge } from "@/components/ui/badge";
import type { RecentRun } from "@/lib/api";
import { severitySeries, severityTone } from "@/lib/incident";

/**
 * 30-day verdict history. Plots the per-day severity score (0 clean to 4
 * critical) from the committed run history embedded in the latest artifact.
 * The scenario rotates by date, so the line genuinely moves run over run.
 */
export function VerdictHistory({ runs }: { runs?: RecentRun[] }) {
  const series = severitySeries(runs);
  const count = runs?.length ?? 0;
  const latest = runs && runs.length > 0 ? runs[0] : null;

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between border-b border-border-subtle py-3">
        <CardTitle>30-day verdict history</CardTitle>
        <Badge variant="outline">{count} run{count === 1 ? "" : "s"}</Badge>
      </CardHeader>
      <CardContent className="p-5">
        {series.length >= 2 ? (
          <>
            <div className="text-brand">
              <Sparkline
                data={series}
                width={520}
                height={56}
                className="w-full"
                color="currentColor"
              />
            </div>
            <p className="mt-2 text-2xs text-foreground-subtle">
              Severity per scan, 0 clean to 4 critical. The nightly cron rotates
              the drift scenario by date.
            </p>
          </>
        ) : (
          <div className="flex flex-col gap-1">
            <p className="text-sm text-foreground-muted">
              History builds as the nightly scan runs.
            </p>
            <p className="text-2xs text-foreground-subtle">
              {latest
                ? `First scan recorded ${latest.date} (${latest.severity}).`
                : "No scans recorded yet."}
            </p>
          </div>
        )}
        {latest && (
          <div className="mt-3 flex items-center gap-2">
            <Badge variant={severityTone(latest.severity)}>
              latest: {latest.severity}
            </Badge>
            <span className="text-2xs text-foreground-subtle">{latest.date}</span>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
