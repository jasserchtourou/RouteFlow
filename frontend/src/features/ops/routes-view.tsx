"use client";

import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { AlertTriangle, ArrowRight } from "lucide-react";
import { DataTable, type Column } from "@/components/data/data-table";
import { Drawer, DrawerSection, Facts } from "@/components/data/drawer";
import { ChipFilter, FilterBar, SearchField, ToggleChip } from "@/components/data/filter-bar";
import { Pagination } from "@/components/data/pagination";
import { Badge } from "@/components/ui/badge";
import { PAGE_SIZE, useListState } from "@/hooks/use-list-state";
import { apiGet } from "@/lib/api";
import { formatDateTime, formatDuration } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { RouteDetailItem, RouteItem } from "./api-types";
import {
  RISK_LEVELS,
  ROUTE_STATUSES,
  label,
  options,
  riskTone,
  routeStatusTone,
  shipmentTone,
} from "./labels";
import { QueryError } from "./query-error";
import { usePageQuery } from "./use-page-query";

const DEFAULT_SORT = "route_number";
const SORT_FOR_TABLE = ["route_number", "distance", "-distance", "-planned_risk"];

/** A 0-100 score as a labelled bar (the number is text, so colour is never the only signal). */
function RiskMeter({ route }: { route: RouteItem }) {
  const { score, level } = route.risk;
  return (
    <span className="flex items-center gap-2">
      <span
        role="meter"
        aria-label="Risk score"
        aria-valuenow={score}
        aria-valuemin={0}
        aria-valuemax={100}
        className="h-1.5 w-16 overflow-hidden rounded-full bg-surface-hover"
      >
        <span
          className={cn(
            "block h-full rounded-full",
            level === "CRITICAL" || level === "HIGH"
              ? "bg-danger"
              : level === "MEDIUM"
                ? "bg-warning"
                : "bg-success",
          )}
          style={{ width: `${score}%` }}
        />
      </span>
      <span className="tabular-nums">{score}</span>
      <Badge tone={riskTone(level)}>{label(level)}</Badge>
    </span>
  );
}

const COLUMNS: Column<RouteItem>[] = [
  {
    key: "number",
    header: "Route",
    sortKey: "route_number",
    cell: (r) => <span className="font-mono">{r.route_number}</span>,
  },
  {
    key: "path",
    header: "Path",
    cell: (r) => (
      <span className="inline-flex items-center gap-1.5 whitespace-nowrap">
        {r.origin} <ArrowRight aria-hidden className="size-3 text-muted" /> {r.destination}
      </span>
    ),
  },
  {
    key: "distance",
    header: "Distance",
    sortKey: "distance",
    align: "right",
    cell: (r) =>
      `${Math.round(r.distance_km)} km · ${formatDuration(r.estimated_duration_minutes)}`,
  },
  {
    key: "status",
    header: "Status",
    cell: (r) => <Badge tone={routeStatusTone(r.status)}>{label(r.status)}</Badge>,
  },
  { key: "risk", header: "Risk", sortKey: "-planned_risk", cell: (r) => <RiskMeter route={r} /> },
  {
    key: "load",
    header: "Shipments",
    align: "right",
    cell: (r) => (
      <span className="inline-flex items-center justify-end gap-2">
        {r.active_shipments} active
        {r.delayed_shipments > 0 && (
          <span className="inline-flex items-center gap-1 text-danger">
            <AlertTriangle aria-hidden className="size-3.5" />
            {r.delayed_shipments} late
          </span>
        )}
      </span>
    ),
  },
];

function RouteDrawer({ number, onClose }: { number: string; onClose: () => void }) {
  const route = useQuery({
    queryKey: ["route", number],
    queryFn: ({ signal }) =>
      apiGet<RouteDetailItem>(`/routes/by-number/${number}`, undefined, signal),
  });
  const r = route.data;

  return (
    <Drawer
      title={number}
      subtitle={r ? `${r.origin} → ${r.destination}` : undefined}
      onClose={onClose}
    >
      {route.isError && (
        <p role="alert" className="text-sm text-danger">
          This route could not be loaded.
        </p>
      )}
      {r && (
        <>
          <div className="rounded-lg bg-background/60 p-3">
            <RiskMeter route={r} />
            <p className="mt-2 text-xs text-muted">Why this score</p>
            {r.risk.factors.length ? (
              <ul className="mt-1 list-disc space-y-1 pl-5 text-sm">
                {r.risk.factors.map((factor) => (
                  <li key={factor}>{factor}</li>
                ))}
              </ul>
            ) : (
              <p className="mt-1 text-sm">Nothing is adding to the risk of this route right now.</p>
            )}
          </div>
          <div className="mt-4">
            <Facts
              items={[
                [
                  "Status",
                  <Badge key="s" tone={routeStatusTone(r.status)}>
                    {label(r.status)}
                  </Badge>,
                ],
                ["Distance", `${Math.round(r.distance_km)} km`],
                ["Planned duration", formatDuration(r.estimated_duration_minutes)],
                ["Planned risk", label(r.planned_risk_level)],
                [
                  "Longest delay",
                  r.max_delay_minutes > 0 ? formatDuration(r.max_delay_minutes) : "None",
                ],
                ["Serious exceptions", r.serious_exceptions],
              ]}
            />
          </div>
          <DrawerSection title={`Shipments on this route (${r.shipments.length})`}>
            {r.shipments.length ? (
              <ul className="flex flex-col gap-2">
                {r.shipments.map((s) => (
                  <li
                    key={s.id}
                    className="flex items-center justify-between gap-3 rounded-lg bg-background/60 p-3 text-sm"
                  >
                    <div className="min-w-0">
                      <p className="font-mono font-medium">{s.shipment_number}</p>
                      <p className="truncate text-xs text-muted">
                        To {s.destination} · ETA {formatDateTime(s.estimated_delivery)}
                      </p>
                    </div>
                    <Badge tone={shipmentTone(s.status, s.is_delayed)}>
                      {s.is_delayed ? `+${formatDuration(s.delay_minutes)}` : label(s.status)}
                    </Badge>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-muted">No active shipments.</p>
            )}
          </DrawerSection>
        </>
      )}
    </Drawer>
  );
}

export function RoutesView() {
  const state = useListState();
  const ranked = state.get("view") === "risk";
  const status = state.list("status");
  const level = state.list("level");
  const q = state.get("q") ?? "";
  const requested = state.get("sort");
  const sort = requested && SORT_FOR_TABLE.includes(requested) ? requested : DEFAULT_SORT;
  const open = state.get("open");
  const delayed = state.get("delayed") === "1";
  const minLevel = state.get("min") ?? "MEDIUM";

  const all = usePageQuery<RouteItem>(
    "routes",
    "/routes",
    {
      status: status.length ? status : undefined,
      planned_risk_level: level.length ? level : undefined,
      search: q || undefined,
      delayed: delayed || undefined,
      sort,
      limit: PAGE_SIZE,
      offset: (state.page - 1) * PAGE_SIZE,
    },
    { refetchMs: undefined },
  );
  // Ranked view: the backend scores every active route and returns the worst first.
  const atRisk = useQuery({
    queryKey: ["routes-at-risk", minLevel],
    queryFn: ({ signal }) =>
      apiGet<RouteItem[]>("/routes/at-risk", { limit: 50, min_level: minLevel }, signal),
    enabled: ranked,
    placeholderData: keepPreviousData,
    refetchInterval: 30_000,
  });

  const active = ranked ? atRisk : all;
  const rows = ranked ? atRisk.data : all.data?.items;

  return (
    <>
      <div
        role="tablist"
        aria-label="Route view"
        className="mb-4 inline-flex gap-1 rounded-lg bg-surface p-1"
      >
        {[
          { id: "all", text: "All routes" },
          { id: "risk", text: "Highest risk first" },
        ].map((tab) => {
          const on = (tab.id === "risk") === ranked;
          return (
            <button
              key={tab.id}
              role="tab"
              type="button"
              aria-selected={on}
              onClick={() => state.update({ view: tab.id === "risk" ? "risk" : null })}
              className={cn(
                "rounded-md px-3 py-1.5 text-sm font-medium transition-colors",
                on ? "bg-background text-foreground shadow" : "text-muted hover:text-foreground",
              )}
            >
              {tab.text}
            </button>
          );
        })}
      </div>

      {ranked ? (
        <FilterBar>
          <span className="text-sm text-muted">Show routes rated at least</span>
          <ChipFilter
            label="Minimum risk level"
            options={options(RISK_LEVELS)}
            selected={[minLevel]}
            onChange={(next) => state.update({ min: next.find((v) => v !== minLevel) ?? minLevel })}
          />
        </FilterBar>
      ) : (
        <FilterBar>
          <SearchField
            label="Search routes"
            placeholder="Route number or city…"
            value={q}
            onChange={(value) => state.update({ q: value })}
          />
          <ChipFilter
            label="Status"
            options={options(ROUTE_STATUSES)}
            selected={status}
            onChange={(next) => state.update({ status: next })}
          />
          <ChipFilter
            label="Planned risk"
            options={options(RISK_LEVELS)}
            selected={level}
            onChange={(next) => state.update({ level: next })}
          />
          <ToggleChip
            label="Delayed only"
            on={delayed}
            onChange={(on) => state.update({ delayed: on ? "1" : null })}
          />
        </FilterBar>
      )}

      {active.isError && !rows ? (
        <QueryError what="Routes" error={active.error} onRetry={() => void active.refetch()} />
      ) : (
        <>
          <DataTable
            caption={ranked ? "Routes ranked by risk" : "Routes"}
            columns={COLUMNS}
            rows={rows}
            rowKey={(r) => r.route_number}
            loading={active.isFetching}
            sort={ranked ? undefined : sort}
            onSort={
              ranked
                ? undefined
                : (next) => state.update({ sort: next === DEFAULT_SORT ? null : next })
            }
            selectedKey={open}
            onSelect={(r) => state.update({ open: r.route_number })}
            emptyTitle={ranked ? "No route is at this risk level" : "No routes match these filters"}
            emptyHint={
              ranked
                ? "Good news: nothing needs investigating at this level."
                : "Try removing a filter."
            }
          />
          {!ranked && (
            <Pagination
              page={state.page}
              pageSize={PAGE_SIZE}
              total={all.data?.total}
              onPage={(page) => state.update({ page: String(page) })}
            />
          )}
        </>
      )}

      {open && <RouteDrawer number={open} onClose={() => state.update({ open: null })} />}
    </>
  );
}
