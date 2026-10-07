"use client";

import { Check, Truck } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Panel } from "@/components/ui/panel";
import { humanize } from "@/features/tracking/mappers";
import { cn } from "@/lib/utils";
import type { SiteVisit } from "../model";
import { trackerSteps } from "../tracker";

export function ShipmentTracker({
  visit,
  defaultOpen = true,
}: {
  visit: SiteVisit | undefined;
  defaultOpen?: boolean;
}) {
  const steps = visit ? trackerSteps(visit) : [];
  const summary = visit ? `${visit.truckCode} · ${humanize(visit.state)}` : "No trucks";

  return (
    <Panel
      id="tracker"
      title="Shipment tracking"
      icon={Truck}
      summary={summary}
      defaultOpen={defaultOpen}
    >
      {!visit ? (
        <p className="text-sm text-muted">No trucks on site right now.</p>
      ) : (
        <>
          <p className="mb-3 truncate text-xs text-muted">
            {visit.truckCode} · {visit.carrier}
          </p>
          <ol className="grid grid-cols-4 gap-1 sm:grid-cols-5">
            {steps.map((step) => (
              <li
                key={step.label}
                aria-current={step.status === "active" ? "step" : undefined}
                className="flex flex-col items-center gap-1 text-center"
              >
                <span
                  className={cn(
                    "grid size-7 place-items-center rounded-full border-2 text-xs",
                    step.status === "done" && "border-accent bg-accent text-accent-fg",
                    step.status === "active" && "border-accent bg-accent/20 text-accent",
                    step.status === "todo" && "border-border text-muted",
                  )}
                >
                  {step.status === "done" ? <Check aria-hidden className="size-3.5" /> : null}
                </span>
                <span
                  className={cn(
                    "text-[11px] leading-tight",
                    step.status === "todo" ? "text-muted" : "font-medium",
                  )}
                >
                  {step.label}
                </span>
                {step.detail && <span className="text-[10px] text-muted">{step.detail}</span>}
              </li>
            ))}
          </ol>

          {visit.shipment && (
            <div className="mt-3 flex items-center justify-between gap-3 rounded-lg bg-background/60 p-2.5 text-sm">
              <div className="min-w-0">
                <p className="truncate font-mono font-medium">#{visit.shipment.number}</p>
                <p className="truncate text-xs text-muted">To: {visit.shipment.destination}</p>
              </div>
              <div className="flex shrink-0 flex-col items-end gap-1">
                <Badge tone="info">{humanize(visit.state)}</Badge>
                <span className="text-xs text-muted">
                  {visit.dockCode}
                  {visit.minutesRemaining !== null ? ` · ${visit.minutesRemaining} min left` : ""}
                </span>
              </div>
            </div>
          )}
        </>
      )}
    </Panel>
  );
}
