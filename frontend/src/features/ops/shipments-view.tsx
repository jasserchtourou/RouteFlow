"use client";

import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, ArrowRight, Snowflake } from "lucide-react";
import { DataTable, type Column } from "@/components/data/data-table";
import { Drawer, DrawerSection, Facts } from "@/components/data/drawer";
import { ChipFilter, FilterBar, SearchField, ToggleChip } from "@/components/data/filter-bar";
import { Pagination } from "@/components/data/pagination";
import { Badge } from "@/components/ui/badge";
import { PAGE_SIZE, useListState } from "@/hooks/use-list-state";
import { apiGet } from "@/lib/api";
import { formatDateTime, formatDuration } from "@/lib/format";
import type { ShipmentDetailItem, ShipmentItem, TrackingEventItem } from "./api-types";
import {
  SHIPMENT_STATUSES,
  eventDetail,
  eventTone,
  label,
  options,
  severityTone,
  shipmentTone,
} from "./labels";
import { QueryError } from "./query-error";
import { usePageQuery } from "./use-page-query";

const DEFAULT_SORT = "estimated_delivery";

/** What needs attention by default: everything that has not been delivered yet. */
export const OPEN_STATUSES = SHIPMENT_STATUSES.filter((s) => s !== "DELIVERED");

/**
 * The status filter lives in the URL: no parameter means "open shipments", `all` means no
 * filter, otherwise a comma-separated list. (An empty list cannot be a parameter value.)
 */
export function selectedStatuses(param: string | null): string[] {
  if (param === null) return OPEN_STATUSES;
  if (param === "all") return [];
  return param.split(",").filter(Boolean);
}

export function statusParam(selected: readonly string[]): string | null {
  if (selected.length === 0) return "all";
  const same =
    selected.length === OPEN_STATUSES.length && OPEN_STATUSES.every((s) => selected.includes(s));
  return same ? null : selected.join(",");
}

const COLUMNS: Column<ShipmentItem>[] = [
  {
    key: "number",
    header: "Shipment",
    sortKey: "shipment_number",
    cell: (s) => (
      <span className="font-mono">
        {s.shipment_number}
        {s.temperature_status !== "NOT_APPLICABLE" && (
          <Snowflake aria-label="Cold chain" className="ml-2 inline size-3.5 text-accent" />
        )}
      </span>
    ),
  },
  {
    key: "order",
    header: "Order",
    cell: (s) => <span className="font-mono text-muted">{s.order_number}</span>,
  },
  {
    key: "route",
    header: "Route",
    cell: (s) => (
      <span className="inline-flex items-center gap-1.5 whitespace-nowrap">
        {s.origin} <ArrowRight aria-hidden className="size-3 text-muted" /> {s.destination}
      </span>
    ),
  },
  {
    key: "status",
    header: "Status",
    cell: (s) => (
      <span className="flex flex-wrap items-center gap-2">
        <Badge tone={shipmentTone(s.status, s.is_delayed)}>{label(s.status)}</Badge>
        {s.is_delayed && (
          <span className="text-xs text-danger">+{formatDuration(s.delay_minutes)}</span>
        )}
      </span>
    ),
  },
  {
    key: "issues",
    header: "Issues",
    cell: (s) =>
      s.active_exception_count > 0 ? (
        <span className="inline-flex items-center gap-1 text-warning">
          <AlertTriangle aria-hidden className="size-3.5" />
          {s.active_exception_count}
          <span className="sr-only"> open exceptions</span>
        </span>
      ) : (
        <span className="text-muted">—</span>
      ),
  },
  {
    key: "eta",
    header: "ETA",
    sortKey: "estimated_delivery",
    align: "right",
    cell: (s) => formatDateTime(s.actual_delivery ?? s.estimated_delivery),
  },
];

function EventLine({ event }: { event: TrackingEventItem }) {
  const detail = eventDetail(event.details);
  return (
    <li className="flex items-start gap-3 py-2.5 text-sm">
      <span aria-hidden className="mt-1.5 size-2 shrink-0 rounded-full bg-accent" />
      <div className="min-w-0 flex-1">
        <p className="flex flex-wrap items-center gap-2">
          <Badge tone={eventTone(event.event_type)}>{label(event.event_type)}</Badge>
          {detail && <span className="text-xs font-medium">{detail}</span>}
        </p>
        <p className="mt-0.5 truncate text-xs text-muted">{event.location}</p>
      </div>
      <time dateTime={event.occurred_at} className="shrink-0 text-xs text-muted">
        {formatDateTime(event.occurred_at)}
      </time>
    </li>
  );
}

function ShipmentDrawer({ number, onClose }: { number: string; onClose: () => void }) {
  const shipment = useQuery({
    queryKey: ["shipment", number],
    queryFn: ({ signal }) =>
      apiGet<ShipmentDetailItem>(`/shipments/by-number/${number}`, undefined, signal),
  });
  const s = shipment.data;
  const history = useQuery({
    queryKey: ["shipment-tracking", s?.id],
    queryFn: ({ signal }) =>
      apiGet<TrackingEventItem[]>(`/shipments/${s?.id}/tracking`, undefined, signal),
    enabled: Boolean(s),
  });

  return (
    <Drawer
      title={number}
      subtitle={s ? `${s.origin} → ${s.destination}` : undefined}
      onClose={onClose}
    >
      {shipment.isError && (
        <p role="alert" className="text-sm text-danger">
          This shipment could not be loaded.
        </p>
      )}
      {s && (
        <>
          <Facts
            items={[
              [
                "Status",
                <Badge key="s" tone={shipmentTone(s.status, s.is_delayed)}>
                  {label(s.status)}
                </Badge>,
              ],
              [
                "Order",
                <span key="o" className="font-mono">
                  {s.order_number}
                </span>,
              ],
              ["Warehouse", s.warehouse_code],
              ["Route", s.route_number ?? "Not assigned"],
              ["Vehicle", s.vehicle_registration ?? "Not assigned"],
              ["Carrier", s.carrier],
              [
                s.actual_delivery ? "Delivered" : "ETA",
                formatDateTime(s.actual_delivery ?? s.estimated_delivery),
              ],
              ["Delay", s.is_delayed ? formatDuration(s.delay_minutes) : "On time"],
              [
                "Temperature",
                s.temperature_status === "NOT_APPLICABLE"
                  ? "Not controlled"
                  : label(s.temperature_status),
              ],
            ]}
          />
          {s.active_exceptions.length > 0 && (
            <DrawerSection title="Open exceptions">
              <ul className="flex flex-col gap-2">
                {s.active_exceptions.map((e) => (
                  <li key={e.id} className="rounded-lg bg-background/60 p-3 text-sm">
                    <p className="flex items-center gap-2">
                      <Badge tone={severityTone(e.severity)}>{label(e.severity)}</Badge>
                      <span className="font-medium">{label(e.type)}</span>
                    </p>
                    <p className="mt-1 text-xs text-muted">{e.description}</p>
                  </li>
                ))}
              </ul>
            </DrawerSection>
          )}
        </>
      )}
      <DrawerSection title="Tracking history">
        {history.isPending && s ? (
          <div className="h-16 animate-pulse rounded-lg bg-surface-hover" />
        ) : history.data?.length ? (
          <ol className="divide-y divide-border/60">
            {[...history.data].reverse().map((event) => (
              <EventLine key={event.id} event={event} />
            ))}
          </ol>
        ) : (
          <p className="text-sm text-muted">No events recorded yet.</p>
        )}
      </DrawerSection>
    </Drawer>
  );
}

export function ShipmentsView() {
  const state = useListState();
  const status = selectedStatuses(state.get("status"));
  const q = state.get("q") ?? "";
  const sort = state.get("sort") ?? DEFAULT_SORT;
  const open = state.get("open");
  const delayed = state.get("delayed") === "1";
  const issues = state.get("issues") === "1";

  const query = usePageQuery<ShipmentItem>("shipments", "/shipments", {
    status: status.length ? status : undefined,
    search: q || undefined,
    delayed: delayed || undefined,
    has_active_exception: issues || undefined,
    sort,
    limit: PAGE_SIZE,
    offset: (state.page - 1) * PAGE_SIZE,
  });

  return (
    <>
      <FilterBar>
        <SearchField
          label="Search shipments"
          placeholder="Shipment or order number…"
          value={q}
          onChange={(value) => state.update({ q: value })}
        />
        <ChipFilter
          label="Status"
          options={options(SHIPMENT_STATUSES)}
          selected={status}
          onChange={(next) => state.update({ status: statusParam(next) })}
        />
        <ToggleChip
          label="Delayed only"
          on={delayed}
          onChange={(on) => state.update({ delayed: on ? "1" : null })}
        />
        <ToggleChip
          label="With exceptions"
          on={issues}
          onChange={(on) => state.update({ issues: on ? "1" : null })}
        />
      </FilterBar>

      {query.isError && !query.data ? (
        <QueryError what="Shipments" error={query.error} onRetry={() => void query.refetch()} />
      ) : (
        <>
          <DataTable
            caption="Shipments"
            columns={COLUMNS}
            rows={query.data?.items}
            rowKey={(s) => s.shipment_number}
            loading={query.isFetching}
            sort={sort}
            onSort={(next) => state.update({ sort: next === DEFAULT_SORT ? null : next })}
            selectedKey={open}
            onSelect={(s) => state.update({ open: s.shipment_number })}
            emptyTitle="No shipments match these filters"
            emptyHint="Try removing a filter, or search for another shipment or order number."
          />
          <Pagination
            page={state.page}
            pageSize={PAGE_SIZE}
            total={query.data?.total}
            onPage={(page) => state.update({ page: String(page) })}
          />
        </>
      )}

      {open && <ShipmentDrawer number={open} onClose={() => state.update({ open: null })} />}
    </>
  );
}
