import { AnimatedBar } from "@/components/ui/animated-bar";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import type { WarehouseSummary } from "./types";

// Thresholds mirror the backend (HIGH >= 85 %, CRITICAL >= 95 %); the UI only picks colours.
function barColor(pct: number): string {
  if (pct >= 95) return "bg-danger";
  if (pct >= 85) return "bg-warning";
  return "bg-accent";
}

function StatusBadge({ status }: { status: WarehouseSummary["status"] }) {
  if (status === "DISRUPTED") return <Badge tone="danger">Disrupted</Badge>;
  if (status === "CONGESTED") return <Badge tone="warning">Congested</Badge>;
  if (status === "OFFLINE") return <Badge>Offline</Badge>;
  return null;
}

export function WarehouseStatus({ warehouses }: { warehouses: WarehouseSummary[] }) {
  return (
    <Card>
      <h2 className="mb-4 text-base font-semibold">Warehouse status</h2>
      <ul className="flex flex-col gap-4">
        {warehouses.map((w) => (
          <li key={w.name}>
            <div className="mb-1.5 flex items-center justify-between gap-2 text-sm">
              <span className="font-medium">{w.name}</span>
              <span className="flex items-center gap-2">
                <StatusBadge status={w.status} />
                {w.lowStockCount > 0 && <Badge tone="warning">{w.lowStockCount} low stock</Badge>}
                <span className="tabular-nums text-muted">{w.utilizationPct}%</span>
              </span>
            </div>
            <div
              role="progressbar"
              aria-label={`${w.name} utilization`}
              aria-valuenow={w.utilizationPct}
              aria-valuemin={0}
              aria-valuemax={100}
              className="h-2 overflow-hidden rounded-full bg-surface-hover"
            >
              <AnimatedBar pct={w.utilizationPct} className={barColor(w.utilizationPct)} />
            </div>
          </li>
        ))}
      </ul>
    </Card>
  );
}
