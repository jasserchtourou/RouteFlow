"use client";

import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/lib/api";
import type {
  DashboardOverviewResponse,
  ExceptionResponse,
  Page,
  ShipmentResponse,
} from "./api-types";
import { toDashboardData } from "./mappers";
import type { DashboardData } from "./types";

export const DASHBOARD_REFRESH_MS = 15_000;

// Everything except DELIVERED: the table is "what still needs attention", soonest ETA first.
const OPEN_STATUSES = [
  "CREATED",
  "PICKED",
  "PACKED",
  "LOADED",
  "IN_TRANSIT",
  "OUT_FOR_DELIVERY",
] as const;

async function fetchDashboard(signal: AbortSignal): Promise<DashboardData> {
  const [overview, shipments, exceptions] = await Promise.all([
    apiGet<DashboardOverviewResponse>("/dashboard/overview", undefined, signal),
    apiGet<Page<ShipmentResponse>>(
      "/shipments",
      { status: OPEN_STATUSES, sort: "estimated_delivery", limit: 6 },
      signal,
    ),
    apiGet<Page<ExceptionResponse>>("/exceptions", { active: true, limit: 6 }, signal),
  ]);
  return toDashboardData(overview, shipments, exceptions, new Date());
}

/** Dashboard data, refreshed automatically so the page behaves like a live control room. */
export function useDashboard() {
  return useQuery({
    queryKey: ["dashboard"],
    queryFn: ({ signal }) => fetchDashboard(signal),
    refetchInterval: DASHBOARD_REFRESH_MS,
  });
}
