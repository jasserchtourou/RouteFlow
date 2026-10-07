"use client";

import { Activity, ArrowDownRight, ArrowUpRight, Clock, Package, Truck } from "lucide-react";
import type { ReactNode } from "react";
import { AnimatedNumber } from "@/components/ui/animated-number";
import { Panel } from "@/components/ui/panel";
import { formatPercent, formatSigned } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { SiteScene } from "../model";

const formatCount = (value: number): string => Math.round(value).toLocaleString("en-US");
const formatPct1 = (value: number): string => formatPercent(value);

function Tile({
  icon,
  label,
  value,
  hint,
  trend,
}: {
  icon: ReactNode;
  label: string;
  value: ReactNode;
  hint: string;
  trend?: number | null;
}) {
  const hasTrend = trend !== null && trend !== undefined;
  const Arrow = hasTrend && trend < 0 ? ArrowDownRight : ArrowUpRight;
  return (
    <div className="flex items-center gap-3 rounded-lg bg-background/60 px-3 py-2.5">
      <span className="grid size-9 shrink-0 place-items-center rounded-lg bg-accent/15 text-accent">
        {icon}
      </span>
      <div className="min-w-0">
        <p className="truncate text-xs text-muted">{label}</p>
        <p className="flex items-baseline gap-1.5">
          <span className="text-xl font-semibold tabular-nums">{value}</span>
          {hasTrend && (
            <span
              className={cn(
                "inline-flex items-center text-xs font-medium",
                trend >= 0 ? "text-success" : "text-danger",
              )}
            >
              <Arrow aria-hidden className="size-3" />
              {formatSigned(trend)}
              <span className="sr-only"> points vs previous 30 days</span>
            </span>
          )}
        </p>
        <p className="truncate text-xs text-muted">{hint}</p>
      </div>
    </div>
  );
}

export function KpiPanel({
  scene,
  defaultOpen = true,
}: {
  scene: SiteScene;
  defaultOpen?: boolean;
}) {
  const { kpis, warehouse } = scene;
  const summary = [
    `${formatCount(kpis.stockOnHand)} pallets`,
    `${kpis.trucksOnSite} trucks`,
    kpis.onTimeRate === null ? null : formatPercent(kpis.onTimeRate),
  ]
    .filter(Boolean)
    .join(" · ");

  return (
    <Panel
      id="kpis"
      label="Site metrics"
      title="Metrics"
      icon={Activity}
      summary={summary}
      defaultOpen={defaultOpen}
    >
      <div className="flex flex-col gap-2">
        <Tile
          icon={<Package aria-hidden className="size-4" />}
          label="Stock on hand"
          value={<AnimatedNumber value={kpis.stockOnHand} format={formatCount} />}
          hint={`pallets · ${warehouse.code}`}
        />
        <Tile
          icon={<Truck aria-hidden className="size-4" />}
          label="Trucks on site"
          value={<AnimatedNumber value={kpis.trucksOnSite} />}
          hint={`${kpis.inboundOnSite} inbound · ${warehouse.code}`}
        />
        <Tile
          icon={<Clock aria-hidden className="size-4" />}
          label="On-time delivery"
          value={
            kpis.onTimeRate === null ? (
              "—"
            ) : (
              <AnimatedNumber value={kpis.onTimeRate} format={formatPct1} />
            )
          }
          hint={`last 30 days · ${warehouse.code}`}
          trend={kpis.onTimeChangePts}
        />
      </div>
    </Panel>
  );
}
