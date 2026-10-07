import type {
  DashboardOverviewResponse,
  ExceptionResponse,
  Page,
  ShipmentResponse,
} from "./api-types";
import type {
  DashboardData,
  FlowStage,
  LiveEvent,
  ShipmentRow,
  ShipmentStatus,
  WarehouseSummary,
} from "./types";

const MS_PER_MIN = 60_000;

const EXCEPTION_TITLE: Record<string, string> = {
  DELAYED: "Delivery delayed",
  TEMPERATURE_DEVIATION: "Temperature deviation",
  DAMAGED: "Goods damaged",
  MISSING_DOCUMENT: "Missing document",
  STOCK_SHORTAGE: "Stock shortage",
};

const PRE_DISPATCH: ShipmentStatus[] = ["CREATED", "PICKED", "PACKED", "LOADED"];

function sumCounts(counts: Record<string, number>, keys: readonly string[]): number {
  return keys.reduce((total, key) => total + (counts[key] ?? 0), 0);
}

export function toFlow(overview: DashboardOverviewResponse): FlowStage[] {
  return [
    { key: "orders", label: "Orders", count: overview.orders.open, caption: "open" },
    {
      key: "warehouse",
      label: "Warehouse",
      count: sumCounts(overview.shipments.by_status, PRE_DISPATCH),
      caption: "picking to loading",
    },
    { key: "shipments", label: "Shipments", count: overview.shipments.active, caption: "active" },
    {
      key: "routes",
      label: "Routes",
      count: overview.fleet.by_status.IN_TRANSIT ?? 0,
      caption: "vehicles on the road",
    },
    {
      key: "delivery",
      label: "Delivery",
      count: overview.shipments.delivered_today,
      caption: "delivered today",
    },
  ];
}

export function toShipmentRow(shipment: ShipmentResponse, now: Date): ShipmentRow {
  const eta = new Date(shipment.estimated_delivery).getTime();
  return {
    shipmentNumber: shipment.shipment_number,
    origin: shipment.origin,
    destination: shipment.destination,
    status: shipment.status as ShipmentStatus,
    etaMinutes: Math.round((eta - now.getTime()) / MS_PER_MIN),
    delayMinutes: shipment.is_delayed ? shipment.delay_minutes : 0,
    coldChain: shipment.temperature_status !== "NOT_APPLICABLE",
  };
}

export function toEvent(exception: ExceptionResponse, now: Date): LiveEvent {
  return {
    id: exception.id,
    shipmentNumber: exception.shipment_number,
    title: EXCEPTION_TITLE[exception.type] ?? exception.type,
    detail: exception.description,
    severity: exception.severity,
    minutesAgo: Math.max(
      0,
      (now.getTime() - new Date(exception.created_at).getTime()) / MS_PER_MIN,
    ),
  };
}

export function toWarehouses(overview: DashboardOverviewResponse): WarehouseSummary[] {
  return overview.warehouses.items
    .map((w) => ({
      name: w.name,
      city: w.location,
      utilizationPct: Math.round(w.utilization_pct),
      lowStockCount: w.low_stock_count,
      status: w.status,
    }))
    .sort((a, b) => b.utilizationPct - a.utilizationPct);
}

export function toDashboardData(
  overview: DashboardOverviewResponse,
  shipments: Page<ShipmentResponse>,
  exceptions: Page<ExceptionResponse>,
  now: Date,
): DashboardData {
  const performance = overview.delivery_performance;
  // Prefer today's rate; before the first delivery of the day fall back to the 7-day rate.
  const onTimeRate = performance.today.on_time_rate ?? performance.last_7_days.on_time_rate;
  return {
    generatedAt: overview.generated_at,
    kpis: {
      activeShipments: overview.shipments.active,
      delayedShipments: overview.shipments.delayed,
      onTimeRate,
      onTimeChangePts: performance.change_vs_yesterday_pts,
      activeExceptions: overview.exceptions.active,
      criticalExceptions: overview.exceptions.critical,
      networkUtilizationPct: overview.warehouses.network_utilization_pct,
      fleetUtilizationPct: overview.fleet.utilization_pct,
      vehiclesOperational: overview.fleet.operational,
      vehiclesTotal: overview.fleet.total,
    },
    flow: toFlow(overview),
    events: exceptions.items.map((item) => toEvent(item, now)),
    shipments: shipments.items.map((item) => toShipmentRow(item, now)),
    warehouses: toWarehouses(overview),
  };
}
