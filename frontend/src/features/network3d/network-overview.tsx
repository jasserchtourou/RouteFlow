"use client";

import { Box, ChevronRight, Globe2 } from "lucide-react";
import dynamic from "next/dynamic";
import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";
import { Card } from "@/components/ui/card";
import { useFleet } from "@/features/tracking/use-fleet";
import { humanize } from "@/features/tracking/mappers";
import { cn } from "@/lib/utils";
import { STATUS_COLOR, buildNetworkLayout, utilizationColor } from "./layout";

// three.js needs WebGL and `window`: the canvas is only ever loaded in the browser.
const NetworkCanvas = dynamic(() => import("./network-canvas"), {
  ssr: false,
  loading: () => <div className="size-full animate-pulse bg-background" />,
});

const LEGEND = [
  ["OPERATIONAL", "Operational"],
  ["CONGESTED", "Congested"],
  ["DISRUPTED", "Disrupted"],
  ["OFFLINE", "Offline"],
] as const;

function Stat({ label, value, tone }: { label: string; value: string; tone?: string }) {
  return (
    <div className="rounded-lg border border-border/70 bg-background/50 px-3 py-1.5">
      <p className="text-[11px] tracking-wide text-muted uppercase">{label}</p>
      <p className={cn("text-base font-semibold tabular-nums", tone)}>{value}</p>
    </div>
  );
}

/**
 * Every warehouse of the network on one isometric board, with the fleet driving between them:
 * the "strategy game" overview. Clicking a site (in the scene or the list) opens its 3D view.
 */
export function NetworkOverview({ className }: { className?: string }) {
  const { data, isError } = useFleet();
  const router = useRouter();
  const [hovered, setHovered] = useState<string | null>(null);

  const layout = useMemo(
    () => (data ? buildNetworkLayout(data.warehouses, data.vehicles) : null),
    [data],
  );

  // Nothing to draw (no sites, or the fleet endpoints failed): the rest of the page stands.
  if (!data || !layout || layout.sites.length === 0) {
    return data || isError ? null : (
      <div
        aria-busy="true"
        aria-label="Loading network"
        className={cn("h-[26rem] animate-pulse rounded-xl bg-surface", className)}
      />
    );
  }

  const open = (id: string) => router.push(`/warehouses/${id}/3d`);
  const inTransit = data.vehicles.filter((v) => v.status === "IN_TRANSIT").length;
  const totalCapacity = data.warehouses.reduce((sum, w) => sum + w.capacity, 0);
  const avgUtil =
    totalCapacity > 0
      ? Math.round(
          data.warehouses.reduce((sum, w) => sum + w.utilizationPct * w.capacity, 0) /
            totalCapacity,
        )
      : 0;
  const alerts = data.warehouses.filter(
    (w) => w.status === "DISRUPTED" || w.status === "CONGESTED",
  ).length;
  const sites = [...layout.sites].sort((a, b) => b.utilizationPct - a.utilizationPct);

  return (
    <Card className={cn("overflow-hidden p-0", className)}>
      <section aria-label="Network overview" className="flex flex-col lg:flex-row">
        <div className="relative h-[24rem] min-w-0 flex-1 sm:h-[28rem]">
          <NetworkCanvas layout={layout} hover={{ hovered, onHover: setHovered, onOpen: open }} />

          {/* HUD: title and headline numbers over the scene */}
          <div className="pointer-events-none absolute inset-x-0 top-0 flex flex-wrap items-start justify-between gap-2 p-3">
            <div className="flex items-center gap-2 rounded-lg border border-border/70 bg-surface/85 px-3 py-2 backdrop-blur">
              <Globe2 aria-hidden className="size-4 text-accent" />
              <h2 className="text-sm font-semibold">Network</h2>
              <span className="relative ml-1 flex size-2">
                <span className="absolute inline-flex size-full animate-ping rounded-full bg-success opacity-75" />
                <span className="relative inline-flex size-2 rounded-full bg-success" />
              </span>
              <span className="text-xs text-muted">live</span>
            </div>
            <div className="flex flex-wrap gap-2 backdrop-blur-sm">
              <Stat label="Sites" value={String(data.warehouses.length)} />
              <Stat label="In transit" value={String(inTransit)} tone="text-accent" />
              <Stat label="Avg fill" value={`${avgUtil}%`} />
              <Stat
                label="Alerts"
                value={String(alerts)}
                tone={alerts > 0 ? "text-warning" : "text-success"}
              />
            </div>
          </div>

          <ul
            aria-label="Site status colours"
            className="pointer-events-none absolute bottom-3 left-3 flex flex-wrap gap-x-3 gap-y-1 rounded-lg border border-border/70 bg-surface/85 px-3 py-1.5 text-[11px] text-muted backdrop-blur"
          >
            {LEGEND.map(([status, label]) => (
              <li key={status} className="flex items-center gap-1.5">
                <span
                  aria-hidden
                  className="size-2 rounded-full"
                  style={{ background: STATUS_COLOR[status] }}
                />
                {label}
              </li>
            ))}
            <li className="hidden items-center gap-1.5 sm:flex">
              <span aria-hidden className="h-2.5 w-1.5 rounded-sm bg-accent" />
              Silo = fill level
            </li>
          </ul>
          <p className="pointer-events-none absolute right-3 bottom-3 hidden text-[11px] text-muted md:block">
            Drag to pan · right-drag to rotate · scroll to zoom
          </p>
        </div>

        {/* The same information as a list: keyboard and screen-reader friendly */}
        <div className="border-t border-border lg:w-72 lg:border-t-0 lg:border-l">
          <h3 className="px-4 pt-3 pb-1 text-xs font-medium tracking-wide text-muted uppercase">
            Sites
          </h3>
          <ul className="max-h-72 overflow-y-auto p-2 lg:max-h-[25rem]">
            {sites.map((site) => (
              <li key={site.id}>
                <button
                  type="button"
                  onClick={() => open(site.id)}
                  onMouseEnter={() => setHovered(site.id)}
                  onMouseLeave={() => setHovered(null)}
                  onFocus={() => setHovered(site.id)}
                  onBlur={() => setHovered(null)}
                  aria-label={`Open 3D view of ${site.name}`}
                  className={cn(
                    "group flex w-full items-center gap-3 rounded-lg px-2 py-2 text-left text-sm transition-colors hover:bg-surface-hover",
                    hovered === site.id && "bg-surface-hover",
                  )}
                >
                  <span
                    aria-hidden
                    className="size-2.5 shrink-0 rounded-full"
                    style={{ background: STATUS_COLOR[site.status] }}
                  />
                  <span className="min-w-0 flex-1">
                    <span className="block truncate font-medium">{site.name}</span>
                    <span className="flex items-center gap-2 text-xs text-muted">
                      <span>{humanize(site.status)}</span>
                      {site.lowStockCount > 0 && (
                        <span className="text-warning">{site.lowStockCount} low stock</span>
                      )}
                    </span>
                  </span>
                  <span className="flex w-12 flex-col items-end gap-1">
                    <span className="text-xs tabular-nums">{site.utilizationPct}%</span>
                    <span className="h-1 w-full overflow-hidden rounded-full bg-surface-hover">
                      <span
                        className="block h-full rounded-full"
                        style={{
                          width: `${site.utilizationPct}%`,
                          background: utilizationColor(site.utilizationPct),
                        }}
                      />
                    </span>
                  </span>
                  <Box aria-hidden className="size-4 shrink-0 text-muted group-hover:hidden" />
                  <ChevronRight
                    aria-hidden
                    className="hidden size-4 shrink-0 text-accent group-hover:block"
                  />
                </button>
              </li>
            ))}
          </ul>
        </div>
      </section>
    </Card>
  );
}
