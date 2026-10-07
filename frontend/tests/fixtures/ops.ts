import { vi } from "vitest";

export const order = (n: number, overrides: Record<string, unknown> = {}) => ({
  id: `o${n}`,
  order_number: `ORD-${10000 + n}`,
  customer_name: `Customer ${n}`,
  origin: "Hannover",
  destination: "Hamburg",
  status: "CONFIRMED",
  priority: "NORMAL",
  promised_delivery_at: "2026-10-09T12:00:00Z",
  created_at: "2026-10-07T08:00:00Z",
  ...overrides,
});

export const shipment = (n: number, overrides: Record<string, unknown> = {}) => ({
  id: `s${n}`,
  shipment_number: `SHP-${2200 + n}`,
  status: "IN_TRANSIT",
  order_number: `ORD-${10000 + n}`,
  warehouse_code: "WH-HAN",
  route_number: "RTE-101",
  vehicle_registration: "B-RF 1074",
  origin: "Hannover",
  destination: "Hamburg",
  carrier: "RouteFlow Logistics",
  estimated_delivery: "2026-10-07T18:00:00Z",
  actual_delivery: null,
  temperature_status: "NOT_APPLICABLE",
  is_delayed: false,
  delay_minutes: 0,
  active_exception_count: 0,
  ...overrides,
});

export const route = (n: number, overrides: Record<string, unknown> = {}) => ({
  id: `r${n}`,
  route_number: `RTE-${100 + n}`,
  origin: "Hannover",
  destination: "Berlin",
  distance_km: 285,
  estimated_duration_minutes: 190,
  status: "ACTIVE",
  planned_risk_level: "MEDIUM",
  active_shipments: 4,
  delayed_shipments: 2,
  max_delay_minutes: 95,
  serious_exceptions: 1,
  risk: { score: 62, level: "HIGH", factors: ["2 delayed shipments", "Worst delay 95 min"] },
  ...overrides,
});

export const feedEvent = (n: number, overrides: Record<string, unknown> = {}) => ({
  id: `e${n}`,
  shipment_id: `s${n}`,
  shipment_number: `SHP-${2200 + n}`,
  origin: "Hannover",
  destination: "Berlin",
  event_type: "CHECKPOINT",
  location: "A2 near Magdeburg",
  occurred_at: new Date(Date.now() - 5 * 60_000).toISOString(),
  details: {},
  ...overrides,
});

export const page = <T>(items: T[], total = items.length, offset = 0) => ({
  items,
  total,
  limit: 20,
  offset,
});

type Handler = (url: URL) => unknown;

/** Routes fetch calls by pathname and records every request URL for assertions. */
export function mockBackend(handlers: Record<string, Handler>) {
  const calls: URL[] = [];
  vi.stubGlobal(
    "fetch",
    vi.fn((input: string | URL | Request) => {
      const url = new URL(String(input));
      calls.push(url);
      const path = url.pathname.replace("/api/v1", "");
      const handler = handlers[path];
      return Promise.resolve(
        handler
          ? Response.json(handler(url))
          : Response.json({ error: { message: "Not found" } }, { status: 404 }),
      );
    }),
  );
  return {
    calls,
    last: (path: string) => [...calls].reverse().find((u) => u.pathname.endsWith(path)),
    all: (path: string) => calls.filter((u) => u.pathname.endsWith(path)),
  };
}
