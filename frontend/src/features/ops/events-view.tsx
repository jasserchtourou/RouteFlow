"use client";

import { ArrowRight } from "lucide-react";
import Link from "next/link";
import { DataTable, type Column } from "@/components/data/data-table";
import { ChipFilter, FilterBar, SearchField } from "@/components/data/filter-bar";
import { Pagination } from "@/components/data/pagination";
import { Badge } from "@/components/ui/badge";
import { PAGE_SIZE, useListState } from "@/hooks/use-list-state";
import { formatAgo, formatDateTime } from "@/lib/format";
import type { FeedEventItem } from "./api-types";
import { EVENT_TYPES, eventDetail, eventTone, label, options } from "./labels";
import { QueryError } from "./query-error";
import { usePageQuery } from "./use-page-query";

const REFRESH_MS = 10_000;

const RANGES = [
  { value: "1h", label: "Last hour", minutes: 60 },
  { value: "24h", label: "Last 24 hours", minutes: 24 * 60 },
  { value: "7d", label: "Last 7 days", minutes: 7 * 24 * 60 },
] as const;

const COLUMNS: Column<FeedEventItem>[] = [
  {
    key: "time",
    header: "When",
    cell: (e) => (
      <time
        dateTime={e.occurred_at}
        title={formatDateTime(e.occurred_at)}
        className="whitespace-nowrap"
      >
        {formatAgo((Date.now() - new Date(e.occurred_at).getTime()) / 60_000)}
      </time>
    ),
  },
  {
    key: "type",
    header: "Event",
    cell: (e) => {
      const detail = eventDetail(e.details);
      return (
        <span className="flex flex-wrap items-center gap-2">
          <Badge tone={eventTone(e.event_type)}>{label(e.event_type)}</Badge>
          {detail && <span className="text-xs font-medium">{detail}</span>}
        </span>
      );
    },
  },
  {
    key: "shipment",
    header: "Shipment",
    cell: (e) => (
      <Link
        href={`/shipments?open=${e.shipment_number}`}
        className="font-mono hover:text-accent"
        onClick={(event) => event.stopPropagation()}
      >
        {e.shipment_number}
      </Link>
    ),
  },
  {
    key: "route",
    header: "Route",
    cell: (e) => (
      <span className="inline-flex items-center gap-1.5 whitespace-nowrap">
        {e.origin} <ArrowRight aria-hidden className="size-3 text-muted" /> {e.destination}
      </span>
    ),
  },
  { key: "location", header: "Location", cell: (e) => e.location },
];

/** Every tracking event in the network, newest first, refreshed every few seconds. */
export function EventsView() {
  const state = useListState();
  const types = state.list("type");
  const q = state.get("q") ?? "";
  const range = RANGES.find((r) => r.value === state.get("range"));

  // Rounded to the minute so the request (and its cache entry) only changes once a minute.
  const minute = Math.floor(Date.now() / 60_000) * 60_000;
  const since = range ? new Date(minute - range.minutes * 60_000).toISOString() : undefined;

  const query = usePageQuery<FeedEventItem>(
    "events",
    "/events",
    {
      event_type: types.length ? types : undefined,
      search: q || undefined,
      since,
      limit: PAGE_SIZE,
      offset: (state.page - 1) * PAGE_SIZE,
    },
    { refetchMs: REFRESH_MS },
  );

  return (
    <>
      <FilterBar>
        <SearchField
          label="Search events"
          placeholder="Shipment, city or location…"
          value={q}
          onChange={(value) => state.update({ q: value })}
        />
        <ChipFilter
          label="Time range"
          options={RANGES.map(({ value, label: text }) => ({ value, label: text }))}
          selected={range ? [range.value] : []}
          onChange={(next) => state.update({ range: next.find((v) => v !== range?.value) ?? null })}
        />
      </FilterBar>
      <FilterBar>
        <ChipFilter
          label="Event type"
          options={options(EVENT_TYPES)}
          selected={types}
          onChange={(next) => state.update({ type: next })}
        />
      </FilterBar>

      <p className="mb-3 flex items-center gap-2 text-xs text-muted" aria-live="polite">
        <span className="relative flex size-2">
          {!query.isError && (
            <span className="absolute inline-flex size-full animate-ping rounded-full bg-success opacity-75" />
          )}
          <span
            className={`relative inline-flex size-2 rounded-full ${query.isError ? "bg-warning" : "bg-success"}`}
          />
        </span>
        {query.isError
          ? "Connection lost. Showing the last known events, retrying…"
          : query.dataUpdatedAt
            ? `Live · updated ${new Date(query.dataUpdatedAt).toLocaleTimeString("de-DE")}`
            : "Loading…"}
      </p>

      {query.isError && !query.data ? (
        <QueryError what="Events" error={query.error} onRetry={() => void query.refetch()} />
      ) : (
        <>
          <DataTable
            caption="Tracking events, newest first"
            columns={COLUMNS}
            rows={query.data?.items}
            rowKey={(e) => e.id}
            loading={query.isFetching}
            emptyTitle="No events match these filters"
            emptyHint="Try a wider time range or remove an event type."
          />
          <Pagination
            page={state.page}
            pageSize={PAGE_SIZE}
            total={query.data?.total}
            onPage={(page) => state.update({ page: String(page) })}
          />
        </>
      )}
    </>
  );
}
