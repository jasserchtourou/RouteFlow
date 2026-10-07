"use client";

import { useQuery } from "@tanstack/react-query";
import { Box } from "lucide-react";
import Link from "next/link";
import { AnimatedBar } from "@/components/ui/animated-bar";
import { Badge, type Tone } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { Reveal } from "@/components/ui/reveal";
import type { Page } from "@/features/dashboard/api-types";
import { humanize } from "@/features/tracking/mappers";
import { ApiError, apiGet } from "@/lib/api";

interface WarehouseItem {
  id: string;
  code: string;
  name: string;
  location: string;
  capacity: number;
  current_utilization: number;
  utilization_pct: number;
  status: string;
  sku_count: number;
  low_stock_count: number;
}

const STATUS_TONE: Record<string, Tone> = {
  OPERATIONAL: "success",
  CONGESTED: "warning",
  DISRUPTED: "danger",
  OFFLINE: "neutral",
};

function barColor(pct: number): string {
  if (pct >= 95) return "bg-danger";
  if (pct >= 85) return "bg-warning";
  return "bg-accent";
}

export function WarehouseList() {
  const { data, isPending, error } = useQuery({
    queryKey: ["warehouses"],
    queryFn: ({ signal }) => apiGet<Page<WarehouseItem>>("/warehouses", { limit: 100 }, signal),
  });

  if (isPending) {
    return (
      <div
        aria-busy="true"
        aria-label="Loading warehouses"
        className="h-48 animate-pulse rounded-xl bg-surface"
      />
    );
  }
  if (error) {
    return (
      <Card role="alert" className="py-10 text-center text-sm text-muted">
        {error instanceof ApiError ? error.message : "Could not load warehouses."}
      </Card>
    );
  }

  return (
    <Reveal className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
      {data.items.map((site) => (
        <Card key={site.id} className="flex flex-col gap-4">
          <div className="flex items-start justify-between gap-2">
            <div>
              <p className="text-xs text-muted">
                {site.code} · {site.location}
              </p>
              <h2 className="text-base font-semibold">{site.name}</h2>
            </div>
            <Badge tone={STATUS_TONE[site.status] ?? "neutral"}>{humanize(site.status)}</Badge>
          </div>
          <div>
            <div className="mb-1.5 flex justify-between text-sm">
              <span className="text-muted">Utilization</span>
              <span className="tabular-nums">{Math.round(site.utilization_pct)}%</span>
            </div>
            <div
              role="progressbar"
              aria-label={`${site.name} utilization`}
              aria-valuenow={Math.round(site.utilization_pct)}
              aria-valuemin={0}
              aria-valuemax={100}
              className="h-2 overflow-hidden rounded-full bg-surface-hover"
            >
              <AnimatedBar
                pct={Math.round(site.utilization_pct)}
                className={barColor(site.utilization_pct)}
              />
            </div>
            <p className="mt-1.5 text-xs text-muted">
              {site.current_utilization.toLocaleString("en-US")} of{" "}
              {site.capacity.toLocaleString("en-US")} pallet positions · {site.sku_count} SKUs
              {site.low_stock_count > 0 ? ` · ${site.low_stock_count} low stock` : ""}
            </p>
          </div>
          <Link
            href={`/warehouses/${site.id}/3d`}
            className="mt-auto inline-flex h-10 items-center justify-center gap-2 rounded-lg bg-accent px-4 text-sm font-medium text-accent-fg hover:opacity-90"
          >
            <Box aria-hidden className="size-4" />
            Open 3D view
          </Link>
        </Card>
      ))}
    </Reveal>
  );
}
