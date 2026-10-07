/** View-models the dashboard components render. `mappers.ts` builds them from API responses. */

export type ShipmentStatus =
  "CREATED" | "PICKED" | "PACKED" | "LOADED" | "IN_TRANSIT" | "OUT_FOR_DELIVERY" | "DELIVERED";

export type Severity = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

export interface DashboardKpis {
  activeShipments: number;
  delayedShipments: number;
  /** null until something has been delivered in the window. */
  onTimeRate: number | null;
  onTimeChangePts: number | null;
  activeExceptions: number;
  criticalExceptions: number;
  networkUtilizationPct: number | null;
  fleetUtilizationPct: number | null;
  vehiclesOperational: number;
  vehiclesTotal: number;
}

/** Counts per stage of Order -> Warehouse -> Shipment -> Route -> Delivery. */
export interface FlowStage {
  key: "orders" | "warehouse" | "shipments" | "routes" | "delivery";
  label: string;
  count: number;
  caption: string;
}

export interface LiveEvent {
  id: string;
  shipmentNumber: string;
  title: string;
  detail: string;
  severity: Severity | "INFO";
  minutesAgo: number;
}

export interface ShipmentRow {
  shipmentNumber: string;
  origin: string;
  destination: string;
  status: ShipmentStatus;
  /** Minutes until the ETA; negative when the ETA has passed. */
  etaMinutes: number;
  delayMinutes: number;
  coldChain: boolean;
}

export interface WarehouseSummary {
  name: string;
  city: string;
  utilizationPct: number;
  lowStockCount: number;
  status: "OPERATIONAL" | "CONGESTED" | "DISRUPTED" | "OFFLINE";
}

export interface DashboardData {
  generatedAt: string;
  kpis: DashboardKpis;
  flow: FlowStage[];
  events: LiveEvent[];
  shipments: ShipmentRow[];
  warehouses: WarehouseSummary[];
}
