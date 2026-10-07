"use client";

import { Fuel } from "lucide-react";
import { Badge, type Tone } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { humanize } from "./mappers";
import type { MapVehicle, VehicleStatus } from "./types";

const STATUS_TONE: Record<VehicleStatus, Tone> = {
  IN_TRANSIT: "info",
  AVAILABLE: "success",
  MAINTENANCE: "warning",
  OFFLINE: "neutral",
};

interface VehicleListProps {
  vehicles: MapVehicle[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}

export function VehicleList({ vehicles, selectedId, onSelect }: VehicleListProps) {
  if (vehicles.length === 0) {
    return <p className="p-4 text-sm text-muted">No vehicles match this filter.</p>;
  }
  return (
    <ul className="divide-y divide-border">
      {vehicles.map((v) => {
        const selected = v.id === selectedId;
        return (
          <li key={v.id}>
            <button
              type="button"
              onClick={() => onSelect(v.id)}
              aria-pressed={selected}
              className={cn(
                "flex w-full flex-col gap-1.5 px-4 py-3 text-left transition-colors hover:bg-surface-hover",
                selected && "bg-accent/10",
              )}
            >
              <span className="flex items-center justify-between gap-2">
                <span className="font-mono text-sm font-medium">{v.registration}</span>
                <Badge tone={STATUS_TONE[v.status]}>{humanize(v.status)}</Badge>
              </span>
              <span className="flex items-center justify-between gap-2 text-xs text-muted">
                <span>
                  {v.type}
                  {v.driver ? ` · ${v.driver}` : ""}
                </span>
                <span
                  className={cn(
                    "inline-flex items-center gap-1 tabular-nums",
                    v.lowFuel && "text-danger",
                  )}
                >
                  <Fuel aria-hidden className="size-3.5" />
                  {Math.round(v.fuelLevel)}%
                  {v.lowFuel && <span className="sr-only"> low fuel</span>}
                </span>
              </span>
              {selected && v.shipments.length > 0 && (
                <span className="flex flex-wrap gap-1.5 pt-1">
                  {v.shipments.map((s) => (
                    <span key={s} className="rounded bg-background px-1.5 py-0.5 font-mono text-xs">
                      {s}
                    </span>
                  ))}
                </span>
              )}
            </button>
          </li>
        );
      })}
    </ul>
  );
}
