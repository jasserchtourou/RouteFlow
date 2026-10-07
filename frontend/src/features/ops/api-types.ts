/** Backend response shapes used by the Orders, Shipments, Routes and Events pages. */

export interface Page<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

export interface OrderItem {
  id: string;
  order_number: string;
  customer_name: string;
  origin: string;
  destination: string;
  status: string;
  priority: string;
  promised_delivery_at: string;
  created_at: string;
}

export interface ShipmentItem {
  id: string;
  shipment_number: string;
  status: string;
  order_number: string;
  warehouse_code: string;
  route_number: string | null;
  vehicle_registration: string | null;
  origin: string;
  destination: string;
  carrier: string;
  estimated_delivery: string;
  actual_delivery: string | null;
  temperature_status: "NOT_APPLICABLE" | "NORMAL" | "DEVIATION";
  is_delayed: boolean;
  delay_minutes: number;
  active_exception_count: number;
}

export interface ExceptionItem {
  id: string;
  type: string;
  severity: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  status: string;
  description: string;
  created_at: string;
}

export interface ShipmentDetailItem extends ShipmentItem {
  active_exceptions: ExceptionItem[];
}

export interface TrackingEventItem {
  id: string;
  event_type: string;
  location: string;
  occurred_at: string;
  details: Record<string, unknown>;
}

export interface FeedEventItem extends TrackingEventItem {
  shipment_id: string;
  shipment_number: string;
  origin: string;
  destination: string;
}

export interface RouteItem {
  id: string;
  route_number: string;
  origin: string;
  destination: string;
  distance_km: number;
  estimated_duration_minutes: number;
  status: string;
  planned_risk_level: string;
  active_shipments: number;
  delayed_shipments: number;
  max_delay_minutes: number;
  serious_exceptions: number;
  risk: { score: number; level: string; factors: string[] };
}

export interface RouteDetailItem extends RouteItem {
  shipments: ShipmentItem[];
}
