"use client";

import dynamic from "next/dynamic";
import { useMemo, useState } from "react";
import { RefreshCw, WifiOff } from "lucide-react";
import { Card } from "@/components/ui/card";
import { ApiError } from "@/lib/api";
import { cn } from "@/lib/utils";
import { humanize } from "./mappers";
import { VEHICLE_STATUSES, type VehicleStatus } from "./types";
import { useFleet } from "./use-fleet";
import { VehicleList } from "./vehicle-list";

// Leaflet touches `window` on import, so the map is only ever loaded in the browser.
const FleetMap = dynamic(() => import("./fleet-map"), {
  ssr: false,
  loading: () => <div className="size-full animate-pulse rounded-xl bg-surface" />,
});

type Filter = VehicleStatus | "ALL";

export function TrackingView() {
  const { data, error, isPending, isError, refetch } = useFleet();
  const [filter, setFilter] = useState<Filter>("ALL");
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const counts = useMemo(() => {
    const result: Record<string, number> = { ALL: data?.vehicles.length ?? 0 };
    for (const v of data?.vehicles ?? []) result[v.status] = (result[v.status] ?? 0) + 1;
    return result;
  }, [data]);

  if (isPending) {
    return (
      <div aria-busy="true" aria-label="Loading fleet map" className="grid gap-4 lg:grid-cols-3">
        <div className="h-[60vh] animate-pulse rounded-xl bg-surface lg:col-span-2" />
        <div className="h-[60vh] animate-pulse rounded-xl bg-surface" />
      </div>
    );
  }
  if (isError && !data) {
    const message = error instanceof ApiError ? error.message : "Could not load the fleet.";
    return (
      <Card role="alert" className="flex flex-col items-center gap-3 py-12 text-center">
        <WifiOff aria-hidden className="size-8 text-danger" />
        <p className="font-medium">Fleet map unavailable</p>
        <p className="max-w-md text-sm text-muted">{message}</p>
        <button
          type="button"
          onClick={() => void refetch()}
          className="mt-2 inline-flex h-10 items-center gap-2 rounded-lg bg-accent px-4 text-sm font-medium text-accent-fg hover:opacity-90"
        >
          <RefreshCw aria-hidden className="size-4" />
          Try again
        </button>
      </Card>
    );
  }
  if (!data) return null;

  const visible =
    filter === "ALL" ? data.vehicles : data.vehicles.filter((v) => v.status === filter);

  return (
    <div className="grid gap-4 lg:grid-cols-3">
      {/* `isolate` keeps Leaflet's internal z-indexes below the mobile navigation drawer. */}
      <div className="isolate h-[60vh] min-h-96 overflow-hidden rounded-xl border border-border lg:col-span-2 lg:h-[calc(100dvh-13rem)]">
        <FleetMap
          vehicles={visible}
          warehouses={data.warehouses}
          selectedId={selectedId}
          onSelect={setSelectedId}
        />
      </div>

      <Card className="flex flex-col overflow-hidden p-0 lg:h-[calc(100dvh-13rem)]">
        <div className="border-b border-border p-4">
          <h2 className="mb-3 text-base font-semibold">Fleet</h2>
          <div role="group" aria-label="Filter by status" className="flex flex-wrap gap-2">
            {(["ALL", ...VEHICLE_STATUSES] as Filter[]).map((status) => (
              <button
                key={status}
                type="button"
                aria-pressed={filter === status}
                onClick={() => setFilter(status)}
                className={cn(
                  "h-8 rounded-full border px-3 text-xs font-medium transition-colors",
                  filter === status
                    ? "border-accent bg-accent/15 text-accent"
                    : "border-border text-muted hover:bg-surface-hover",
                )}
              >
                {status === "ALL" ? "All" : humanize(status)} · {counts[status] ?? 0}
              </button>
            ))}
          </div>
          {data.withoutPosition > 0 && (
            <p className="mt-3 text-xs text-warning">
              {data.withoutPosition} vehicle(s) have not reported a position and are not shown.
            </p>
          )}
          {isError && (
            <p role="status" className="mt-3 text-xs text-warning">
              Connection lost. Showing the last known positions, retrying…
            </p>
          )}
        </div>
        <div className="flex-1 overflow-y-auto">
          <VehicleList vehicles={visible} selectedId={selectedId} onSelect={setSelectedId} />
        </div>
      </Card>
    </div>
  );
}
