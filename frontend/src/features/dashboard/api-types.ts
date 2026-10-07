/** The subset of backend responses the dashboard reads (see the FastAPI /docs schemas). */

export interface Page<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

interface DeliveryWindow {
  delivered: number;
  on_time: number;
  on_time_rate: number | null;
}

export interface WarehouseListItem {
  code: string;
  name: string;
  location: string;
  utilization_pct: number;
  status: "OPERATIONAL" | "CONGESTED" | "DISRUPTED" | "OFFLINE";
  low_stock_count: number;
}

export interface DashboardOverviewResponse {
  generated_at: string;
  orders: { open: number; by_status: Record<string, number> };
  shipments: {
    active: number;
    in_transit: number;
    delayed: number;
    delivered_today: number;
    by_status: Record<string, number>;
  };
  exceptions: { active: number; critical: number };
  fleet: {
    total: number;
    operational: number;
    utilization_pct: number | null;
    by_status: Record<string, number>;
  };
  warehouses: {
    network_utilization_pct: number | null;
    items: WarehouseListItem[];
  };
  delivery_performance: {
    today: DeliveryWindow;
    last_7_days: DeliveryWindow;
    change_vs_yesterday_pts: number | null;
  };
}

export interface ShipmentResponse {
  shipment_number: string;
  status: string;
  origin: string;
  destination: string;
  estimated_delivery: string;
  is_delayed: boolean;
  delay_minutes: number;
  temperature_status: "NOT_APPLICABLE" | "NORMAL" | "DEVIATION";
}

export interface ExceptionResponse {
  id: string;
  shipment_number: string;
  destination: string;
  type: string;
  severity: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  description: string;
  created_at: string;
}
