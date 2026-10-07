/** The subset of /vehicles and /warehouses responses the fleet map reads. */

export interface VehicleResponse {
  id: string;
  registration: string;
  vehicle_type: string;
  status: string;
  fuel_level: number;
  low_fuel: boolean;
  position: { latitude: number; longitude: number } | null;
  driver_name: string | null;
  active_shipments: string[];
}

export interface WarehouseMapResponse {
  id: string;
  code: string;
  name: string;
  location: string;
  latitude: number;
  longitude: number;
  utilization_pct: number;
  status: "OPERATIONAL" | "CONGESTED" | "DISRUPTED" | "OFFLINE";
}
