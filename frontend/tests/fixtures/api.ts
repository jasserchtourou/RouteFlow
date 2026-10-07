import type {
  DashboardOverviewResponse,
  ExceptionResponse,
  Page,
  ShipmentResponse,
} from "@/features/dashboard/api-types";

export const NOW = new Date("2026-10-07T12:00:00Z");

export const OVERVIEW: DashboardOverviewResponse = {
  generated_at: "2026-10-07T12:00:00Z",
  orders: { open: 58, by_status: {} },
  shipments: {
    active: 42,
    in_transit: 20,
    delayed: 6,
    delivered_today: 23,
    by_status: { CREATED: 3, PICKED: 4, PACKED: 5, LOADED: 7, IN_TRANSIT: 18, OUT_FOR_DELIVERY: 5 },
  },
  exceptions: { active: 5, critical: 1 },
  fleet: { total: 20, operational: 17, utilization_pct: 68, by_status: { IN_TRANSIT: 12 } },
  warehouses: {
    network_utilization_pct: 72.4,
    items: [
      {
        code: "HAN",
        name: "Hannover Central",
        location: "Hannover",
        utilization_pct: 78.2,
        status: "OPERATIONAL",
        low_stock_count: 1,
      },
      {
        code: "GAR",
        name: "Garbsen DC",
        location: "Garbsen",
        utilization_pct: 96.1,
        status: "DISRUPTED",
        low_stock_count: 4,
      },
    ],
  },
  delivery_performance: {
    today: { delivered: 23, on_time: 21, on_time_rate: 91.3 },
    last_7_days: { delivered: 150, on_time: 141, on_time_rate: 94 },
    change_vs_yesterday_pts: 1.3,
  },
};

export const SHIPMENTS: Page<ShipmentResponse> = {
  items: [
    {
      shipment_number: "SHP-2211",
      status: "IN_TRANSIT",
      origin: "Hamburg",
      destination: "Hannover",
      estimated_delivery: "2026-10-07T11:25:00Z",
      is_delayed: true,
      delay_minutes: 35,
      temperature_status: "DEVIATION",
    },
    {
      shipment_number: "SHP-2215",
      status: "LOADED",
      origin: "Langenhagen",
      destination: "Leipzig",
      estimated_delivery: "2026-10-07T14:40:00Z",
      is_delayed: false,
      delay_minutes: 0,
      temperature_status: "NOT_APPLICABLE",
    },
  ],
  total: 2,
  limit: 6,
  offset: 0,
};

export const EXCEPTIONS: Page<ExceptionResponse> = {
  items: [
    {
      id: "ex-1",
      shipment_number: "SHP-2211",
      destination: "Hannover",
      type: "TEMPERATURE_DEVIATION",
      severity: "CRITICAL",
      description: "Reefer at 11.2 C, limit 8 C",
      created_at: "2026-10-07T11:56:00Z",
    },
  ],
  total: 1,
  limit: 6,
  offset: 0,
};

export const EMPTY_PAGE = { items: [], total: 0, limit: 6, offset: 0 };
