import { ArrowDownRight, ArrowUpRight, type LucideIcon } from "lucide-react";
import { AlertTriangle, Clock, PackageSearch, Truck, Warehouse } from "lucide-react";
import { AnimatedNumber } from "@/components/ui/animated-number";
import { Card } from "@/components/ui/card";
import { Reveal } from "@/components/ui/reveal";
import { cn } from "@/lib/utils";
import { formatPercent, formatSigned } from "@/lib/format";
import type { DashboardKpis } from "./types";

const formatCount = (value: number): string => String(Math.round(value));
const formatPct1 = (value: number): string => formatPercent(value);
const formatPct0 = (value: number): string => formatPercent(value, 0);

interface KpiProps {
  label: string;
  /** null renders as an em dash (nothing measured yet). */
  value: number | null;
  format: (value: number) => string;
  icon: LucideIcon;
  hint: string;
  /** Signed change shown as a trend chip. */
  trend?: number | null;
  alert?: boolean;
}

function Kpi({ label, value, format, icon: Icon, hint, trend, alert }: KpiProps) {
  const hasTrend = trend !== null && trend !== undefined;
  const TrendIcon = hasTrend && trend < 0 ? ArrowDownRight : ArrowUpRight;
  return (
    <Card
      className={cn(
        "flex flex-col gap-3 transition-transform duration-200 hover:-translate-y-0.5",
        alert && "border-danger/50",
      )}
    >
      <div className="flex items-center justify-between text-sm text-muted">
        <span>{label}</span>
        <span className="relative">
          {alert && (
            <span
              aria-hidden
              className="absolute -top-0.5 -right-0.5 size-2 animate-ping rounded-full bg-danger"
            />
          )}
          <Icon aria-hidden className={cn("size-4", alert ? "text-danger" : "text-accent")} />
        </span>
      </div>
      <div className="flex items-baseline gap-2">
        <span className="text-3xl font-semibold tracking-tight tabular-nums">
          {value === null ? "—" : <AnimatedNumber value={value} format={format} />}
        </span>
        {hasTrend && (
          <span
            className={cn(
              "inline-flex items-center text-xs font-medium",
              trend >= 0 ? "text-success" : "text-danger",
            )}
          >
            <TrendIcon aria-hidden className="size-3.5" />
            {formatSigned(trend)} pts
            <span className="sr-only"> vs yesterday</span>
          </span>
        )}
      </div>
      <p className="text-xs text-muted">{hint}</p>
    </Card>
  );
}

export function KpiCards({ kpis }: { kpis: DashboardKpis }) {
  const cards: KpiProps[] = [
    {
      label: "Active shipments",
      value: kpis.activeShipments,
      format: formatCount,
      icon: PackageSearch,
      hint: "not yet delivered",
    },
    {
      label: "Delayed",
      value: kpis.delayedShipments,
      format: formatCount,
      icon: Clock,
      hint: "ETA already passed",
      alert: kpis.delayedShipments > 0,
    },
    {
      label: "On-time delivery",
      value: kpis.onTimeRate,
      format: formatPct1,
      icon: Truck,
      hint: "vs customer promise",
      trend: kpis.onTimeChangePts,
    },
    {
      label: "Open exceptions",
      value: kpis.activeExceptions,
      format: formatCount,
      icon: AlertTriangle,
      hint: `${kpis.criticalExceptions} critical`,
      alert: kpis.criticalExceptions > 0,
    },
    {
      label: "Warehouse utilization",
      value: kpis.networkUtilizationPct,
      format: formatPct0,
      icon: Warehouse,
      hint: "capacity-weighted, all sites",
    },
    {
      label: "Fleet in use",
      value: kpis.fleetUtilizationPct,
      format: formatPct0,
      icon: Truck,
      hint: `${kpis.vehiclesOperational} of ${kpis.vehiclesTotal} vehicles operational`,
    },
  ];
  return (
    <section aria-label="Key metrics">
      <Reveal className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-6">
        {cards.map((card) => (
          <Kpi key={card.label} {...card} />
        ))}
      </Reveal>
    </section>
  );
}
