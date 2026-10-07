"use client";

import { useQuery } from "@tanstack/react-query";
import { ArrowRight } from "lucide-react";
import { DataTable, type Column } from "@/components/data/data-table";
import { Drawer, DrawerSection, Facts } from "@/components/data/drawer";
import { ChipFilter, FilterBar, SearchField } from "@/components/data/filter-bar";
import { Pagination } from "@/components/data/pagination";
import { Badge } from "@/components/ui/badge";
import { PAGE_SIZE, useListState } from "@/hooks/use-list-state";
import { formatDateTime } from "@/lib/format";
import { apiGet } from "@/lib/api";
import type { OrderItem, Page, ShipmentItem } from "./api-types";
import {
  ORDER_PRIORITIES,
  ORDER_STATUSES,
  label,
  options,
  orderStatusTone,
  priorityTone,
  shipmentTone,
} from "./labels";
import { QueryError } from "./query-error";
import { usePageQuery } from "./use-page-query";

const DEFAULT_SORT = "-created_at";

const COLUMNS: Column<OrderItem>[] = [
  {
    key: "number",
    header: "Order",
    sortKey: "order_number",
    cell: (o) => <span className="font-mono">{o.order_number}</span>,
  },
  { key: "customer", header: "Customer", sortKey: "customer_name", cell: (o) => o.customer_name },
  {
    key: "route",
    header: "Route",
    cell: (o) => (
      <span className="inline-flex items-center gap-1.5 whitespace-nowrap">
        {o.origin} <ArrowRight aria-hidden className="size-3 text-muted" /> {o.destination}
      </span>
    ),
  },
  {
    key: "status",
    header: "Status",
    cell: (o) => <Badge tone={orderStatusTone(o.status)}>{label(o.status)}</Badge>,
  },
  {
    key: "priority",
    header: "Priority",
    sortKey: "priority",
    cell: (o) => <Badge tone={priorityTone(o.priority)}>{label(o.priority)}</Badge>,
  },
  {
    key: "promised",
    header: "Promised",
    sortKey: "promised_delivery_at",
    align: "right",
    cell: (o) => formatDateTime(o.promised_delivery_at),
  },
];

function OrderDrawer({ number, onClose }: { number: string; onClose: () => void }) {
  const order = useQuery({
    queryKey: ["order", number],
    queryFn: ({ signal }) => apiGet<OrderItem>(`/orders/by-number/${number}`, undefined, signal),
  });
  const shipments = useQuery({
    queryKey: ["order-shipments", number],
    queryFn: ({ signal }) =>
      apiGet<Page<ShipmentItem>>("/shipments", { search: number, limit: 20 }, signal),
  });
  const o = order.data;

  return (
    <Drawer title={number} subtitle={o?.customer_name} onClose={onClose}>
      {order.isError && (
        <p role="alert" className="text-sm text-danger">
          This order could not be loaded.
        </p>
      )}
      {o && (
        <Facts
          items={[
            [
              "Status",
              <Badge key="s" tone={orderStatusTone(o.status)}>
                {label(o.status)}
              </Badge>,
            ],
            [
              "Priority",
              <Badge key="p" tone={priorityTone(o.priority)}>
                {label(o.priority)}
              </Badge>,
            ],
            ["From", o.origin],
            ["To", o.destination],
            ["Promised delivery", formatDateTime(o.promised_delivery_at)],
            ["Created", formatDateTime(o.created_at)],
          ]}
        />
      )}
      <DrawerSection title="Shipments">
        {shipments.isPending ? (
          <div className="h-12 animate-pulse rounded-lg bg-surface-hover" />
        ) : shipments.data?.items.length ? (
          <ul className="flex flex-col gap-2">
            {shipments.data.items.map((s) => (
              <li
                key={s.id}
                className="flex items-center justify-between gap-3 rounded-lg bg-background/60 p-3 text-sm"
              >
                <div className="min-w-0">
                  <p className="font-mono font-medium">{s.shipment_number}</p>
                  <p className="truncate text-xs text-muted">
                    {s.origin} → {s.destination} · ETA {formatDateTime(s.estimated_delivery)}
                  </p>
                </div>
                <Badge tone={shipmentTone(s.status, s.is_delayed)}>
                  {s.is_delayed ? `Late · ${label(s.status)}` : label(s.status)}
                </Badge>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-muted">No shipments have been created for this order yet.</p>
        )}
      </DrawerSection>
    </Drawer>
  );
}

export function OrdersView() {
  const state = useListState();
  const status = state.list("status");
  const priority = state.list("priority");
  const q = state.get("q") ?? "";
  const sort = state.get("sort") ?? DEFAULT_SORT;
  const open = state.get("open");

  const query = usePageQuery<OrderItem>("orders", "/orders", {
    status: status.length ? status : undefined,
    priority: priority.length ? priority : undefined,
    search: q || undefined,
    sort,
    limit: PAGE_SIZE,
    offset: (state.page - 1) * PAGE_SIZE,
  });

  return (
    <>
      <FilterBar>
        <SearchField
          label="Search orders"
          placeholder="Order number or customer…"
          value={q}
          onChange={(value) => state.update({ q: value })}
        />
        <ChipFilter
          label="Status"
          options={options(ORDER_STATUSES)}
          selected={status}
          onChange={(next) => state.update({ status: next })}
        />
        <ChipFilter
          label="Priority"
          options={options(ORDER_PRIORITIES)}
          selected={priority}
          onChange={(next) => state.update({ priority: next })}
        />
      </FilterBar>

      {query.isError && !query.data ? (
        <QueryError what="Orders" error={query.error} onRetry={() => void query.refetch()} />
      ) : (
        <>
          <DataTable
            caption="Orders"
            columns={COLUMNS}
            rows={query.data?.items}
            rowKey={(o) => o.order_number}
            loading={query.isFetching}
            sort={sort}
            onSort={(next) => state.update({ sort: next === DEFAULT_SORT ? null : next })}
            selectedKey={open}
            onSelect={(o) => state.update({ open: o.order_number })}
            emptyTitle="No orders match these filters"
            emptyHint="Try removing a filter or searching for a different customer."
          />
          <Pagination
            page={state.page}
            pageSize={PAGE_SIZE}
            total={query.data?.total}
            onPage={(page) => state.update({ page: String(page) })}
          />
        </>
      )}

      {open && <OrderDrawer number={open} onClose={() => state.update({ open: null })} />}
    </>
  );
}
