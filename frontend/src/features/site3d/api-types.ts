/** Response of GET /warehouses/{id}/scene (see the FastAPI /docs schema `SceneRead`). */

export type DockDirection = "INBOUND" | "OUTBOUND";
export type DockState = "AVAILABLE" | "BOOKED" | "OCCUPIED" | "OUT_OF_SERVICE";
export type VisitState =
  | "SCHEDULED"
  | "EN_ROUTE"
  | "WAITING"
  | "DOCKED"
  | "LOADING"
  | "UNLOADING"
  | "DEPARTED"
  | "COMPLETED";
export type EquipmentStatus = "ACTIVE" | "IDLE" | "CHARGING" | "MAINTENANCE";
export type StockStatus = "OK" | "LOW" | "OUT_OF_STOCK";

export interface SceneResponse {
  generated_at: string;
  warehouse: {
    id: string;
    code: string;
    name: string;
    location: string;
    status: string;
    capacity: number;
    stock_pallets: number;
    utilization_pct: number;
  };
  kpis: {
    stock_on_hand_pallets: number;
    trucks_on_site: number;
    inbound_trucks_on_site: number;
    docks_occupied: number;
    docks_total: number;
    on_time_rate_30d: number | null;
    on_time_change_pts: number | null;
  };
  layout: { dock_count: number; yard_slots: number };
  timings: { approach_seconds: number; docking_seconds: number; leaving_seconds: number };
  docks: {
    id: string;
    code: string;
    direction: DockDirection;
    position: number;
    state: DockState;
    visit_id: string | null;
    trucks_today: number;
  }[];
  visits: {
    id: string;
    truck_code: string;
    carrier: string;
    direction: DockDirection;
    dock_code: string;
    state: VisitState;
    arrives_at: string;
    docked_at: string;
    departs_at: string;
    pallets_total: number;
    pallets_done: number;
    minutes_remaining: number | null;
    shipment: {
      shipment_number: string;
      destination: string;
      status: string;
      estimated_delivery: string;
    } | null;
  }[];
  equipment: {
    id: string;
    code: string;
    equipment_type: string;
    status: EquipmentStatus;
    battery_level: number;
    assigned_dock_code: string | null;
  }[];
  pallets: {
    id: string;
    sku: string;
    product_name: string;
    quantity: number;
    slot: number;
    stock_status: StockStatus;
    has_issue: boolean;
  }[];
}
