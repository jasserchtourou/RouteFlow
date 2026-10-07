"use client";

import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/lib/api";
import type { Page } from "@/features/dashboard/api-types";
import type { VehicleResponse, WarehouseMapResponse } from "./api-types";
import { toFleetMapData } from "./mappers";
import type { FleetMapData } from "./types";

export const FLEET_REFRESH_MS = 10_000;

async function fetchFleet(signal: AbortSignal): Promise<FleetMapData> {
  // 100 is the backend's maximum page size; the demo network is far smaller.
  const [vehicles, warehouses] = await Promise.all([
    apiGet<Page<VehicleResponse>>("/vehicles", { limit: 100 }, signal),
    apiGet<Page<WarehouseMapResponse>>("/warehouses", { limit: 100 }, signal),
  ]);
  return toFleetMapData(vehicles.items, warehouses.items);
}

export function useFleet() {
  return useQuery({
    queryKey: ["fleet-map"],
    queryFn: ({ signal }) => fetchFleet(signal),
    refetchInterval: FLEET_REFRESH_MS,
  });
}
