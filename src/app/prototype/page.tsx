import { AlertTriangle, ArrowRight, Radar, ShieldAlert, TerminalSquare } from "lucide-react";
import { TopBar } from "@/components/layout/TopBar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { CodeBlock } from "@/components/ui/code-block";
import { INCIDENT_COMMANDS, INCIDENT_DRIFTS, INCIDENT_METRICS, INCIDENT_REPORT } from "@/lib/prototype";

export const metadata = { title: "Prototype Incident" };

export default function PrototypePage() {
  return (
    <>
      <TopBar
        title="Prototype Incident"
        description="A concrete before-vs-after data drift story using the bundled orders snapshots."
        actions={
          <Button asChild size="sm" variant="outline">
            <a href="https://github.com/IgnazioDS/data-quality-watchtower/tree/main/examples" target="_blank" rel="noreferrer">
              Open example data
              <ArrowRight />
            </a>
          </Button>
        }
      />
      <div className="dot-grid grid-fade flex-1 overflow-y-auto">
        <div className="page-enter mx-auto max-w-6xl space-y-5 p-6">
          <Card className="overflow-hidden">
            <CardContent className="grid gap-5 p-6 lg:grid-cols-[1.2fr,0.9fr]">
              <div className="space-y-3">
                <div className="flex flex-wrap items-center gap-1.5">
                  <Badge variant="brand">Prototype</Badge>
                  <Badge variant="danger">Critical incident</Badge>
                  <Badge variant="outline">Orders dataset</Badge>
                </div>
                <h2 className="text-2xl font-semibold tracking-tight text-foreground">
                  The repo now shows a real quality incident, not a hypothetical dashboard alert.
                </h2>
                <p className="max-w-2xl text-sm leading-relaxed text-foreground-muted">
                  A clean baseline snapshot is compared against a degraded candidate snapshot with missing region data,
                  identifier type drift, a sharp row-count drop, and a suspicious revenue spike. The watchtower turns that
                  into a named incident with a failing gate.
                </p>
              </div>
              <div className="grid gap-3 rounded-xl border border-border-subtle bg-surface-2 p-4">
                <div className="flex items-center gap-2 text-sm font-medium text-foreground">
                  <ShieldAlert className="h-4 w-4 text-danger" />
                  Incident summary
                </div>
                <div className="grid grid-cols-2 gap-3">
                  {INCIDENT_METRICS.map((metric) => (
                    <div key={metric.label} className="rounded-lg border border-border bg-surface p-3">
                      <p className="text-2xs uppercase tracking-wider text-foreground-faint">{metric.label}</p>
                      <p className="mt-2 text-lg font-semibold text-foreground">{metric.candidate}</p>
                      <p className="text-xs text-danger">{metric.delta}</p>
                    </div>
                  ))}
                </div>
              </div>
            </CardContent>
          </Card>

          <div className="grid gap-4 lg:grid-cols-[1.1fr,0.9fr]">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Radar className="h-3.5 w-3.5 text-brand" />
                  Drift breakdown
                </CardTitle>
                <CardDescription>
                  The watchtower names the specific failure mode instead of returning a generic anomaly score.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                {INCIDENT_DRIFTS.map((drift) => (
                  <div key={`${drift.category}-${drift.column}`} className="rounded-lg border border-border-subtle bg-surface-2 p-4">
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="text-sm font-semibold text-foreground">{drift.column}</p>
                      <Badge variant="outline">{drift.category}</Badge>
                      <Badge variant={drift.severity === "critical" ? "danger" : "warning"}>{drift.severity}</Badge>
                    </div>
                    <p className="mt-3 text-sm leading-relaxed text-foreground-muted">{drift.summary}</p>
                  </div>
                ))}
              </CardContent>
            </Card>

            <div className="space-y-4">
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <TerminalSquare className="h-3.5 w-3.5 text-brand" />
                    CLI flow
                  </CardTitle>
                  <CardDescription>The repo includes the exact data and commands used to reproduce this incident.</CardDescription>
                </CardHeader>
                <CardContent className="space-y-3">
                  <CodeBlock language="bash">{INCIDENT_COMMANDS.baseline}</CodeBlock>
                  <CodeBlock language="bash">{INCIDENT_COMMANDS.candidate}</CodeBlock>
                  <CodeBlock language="bash">{INCIDENT_COMMANDS.compare}</CodeBlock>
                  <CodeBlock language="bash">{INCIDENT_COMMANDS.gate}</CodeBlock>
                  <CodeBlock language="bash">{INCIDENT_COMMANDS.inspect}</CodeBlock>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <AlertTriangle className="h-3.5 w-3.5 text-danger" />
                    Gate artifact
                  </CardTitle>
                  <CardDescription>
                    A saved report can be attached directly to CI output, review threads, or incident follow-ups.
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <CodeBlock language="md">{INCIDENT_REPORT}</CodeBlock>
                </CardContent>
              </Card>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
