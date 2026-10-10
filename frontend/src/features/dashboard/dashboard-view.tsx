"use client";

import { RefreshCw, WifiOff } from "lucide-react";
import { Card } from "@/components/ui/card";
import { NetworkOverview } from "@/features/network3d/network-overview";
import { ApiError } from "@/lib/api";
import { KpiCards } from "./kpi-cards";
import { LiveEvents } from "./live-events";
import { LogisticsFlow } from "./logistics-flow";
import { ShipmentsTable } from "./shipments-table";
import { useDashboard } from "./use-dashboard";
import { WarehouseStatus } from "./warehouse-status";
import type { DashboardData } from "./types";

function Skeleton({ className }: { className: string }) {
  return <div className={`animate-pulse rounded-xl bg-surface ${className}`} />;
}

function DashboardSkeleton() {
  return (
    <div aria-busy="true" aria-label="Loading dashboard" className="flex flex-col gap-4">
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-6">
        {Array.from({ length: 6 }, (_, i) => (
          <Skeleton key={i} className="h-28" />
        ))}
      </div>
      <Skeleton className="h-28" />
      <div className="grid gap-4 xl:grid-cols-3">
        <Skeleton className="h-72 xl:col-span-2" />
        <Skeleton className="h-72" />
      </div>
    </div>
  );
}

function ErrorPanel({ error, onRetry }: { error: unknown; onRetry: () => void }) {
  const message =
    error instanceof ApiError ? error.message : "Something went wrong loading the dashboard.";
  return (
    <Card role="alert" className="flex flex-col items-center gap-3 py-12 text-center">
      <WifiOff aria-hidden className="size-8 text-danger" />
      <p className="font-medium">Dashboard unavailable</p>
      <p className="max-w-md text-sm text-muted">{message}</p>
      <button
        type="button"
        onClick={onRetry}
        className="mt-2 inline-flex h-10 items-center gap-2 rounded-lg bg-accent px-4 text-sm font-medium text-accent-fg hover:opacity-90"
      >
        <RefreshCw aria-hidden className="size-4" />
        Try again
      </button>
    </Card>
  );
}

function LiveIndicator({ updatedAt, stale }: { updatedAt: number; stale: boolean }) {
  return (
    <p className="mb-4 flex items-center gap-2 text-xs text-muted" aria-live="polite">
      <span className="relative flex size-2">
        {!stale && (
          <span className="absolute inline-flex size-full animate-ping rounded-full bg-success opacity-75" />
        )}
        <span
          className={`relative inline-flex size-2 rounded-full ${stale ? "bg-warning" : "bg-success"}`}
        />
      </span>
      {stale
        ? "Connection lost. Showing the last known data, retrying…"
        : `Live · updated ${new Date(updatedAt).toLocaleTimeString("de-DE")}`}
    </p>
  );
}

function Content({ data }: { data: DashboardData }) {
  return (
    <div className="flex flex-col gap-4">
      <KpiCards kpis={data.kpis} />
      <NetworkOverview />
      <LogisticsFlow stages={data.flow} />
      <div className="grid gap-4 xl:grid-cols-3">
        <div className="xl:col-span-2">
          <ShipmentsTable rows={data.shipments} />
        </div>
        <LiveEvents events={data.events} />
      </div>
      <WarehouseStatus warehouses={data.warehouses} />
    </div>
  );
}

export function DashboardView() {
  const { data, error, isPending, isError, refetch, dataUpdatedAt } = useDashboard();

  if (isPending) return <DashboardSkeleton />;
  // No data at all: show the error. Data present but a refresh failed: keep showing it, flagged stale.
  if (isError && !data) return <ErrorPanel error={error} onRetry={() => void refetch()} />;
  if (!data) return null;

  return (
    <>
      <LiveIndicator updatedAt={dataUpdatedAt} stale={isError} />
      <Content data={data} />
    </>
  );
}
