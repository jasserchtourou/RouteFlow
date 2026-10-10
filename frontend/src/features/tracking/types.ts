export type VehicleStatus = "AVAILABLE" | "IN_TRANSIT" | "MAINTENANCE" | "OFFLINE";

export const VEHICLE_STATUSES: readonly VehicleStatus[] = [
  "IN_TRANSIT",
  "AVAILABLE",
  "MAINTENANCE",
  "OFFLINE",
];

export interface MapVehicle {
  id: string;
  registration: string;
  type: string;
  status: VehicleStatus;
  fuelLevel: number;
  lowFuel: boolean;
  lat: number;
  lng: number;
  driver: string | null;
  shipments: string[];
}

export interface MapWarehouse {
  id: string;
  code: string;
  name: string;
  city: string;
  lat: number;
  lng: number;
  /** Pallet positions. */
  capacity: number;
  utilizationPct: number;
  lowStockCount: number;
  status: "OPERATIONAL" | "CONGESTED" | "DISRUPTED" | "OFFLINE";
}

export interface FleetMapData {
  vehicles: MapVehicle[];
  warehouses: MapWarehouse[];
  /** Vehicles the backend knows but that have not reported a position yet. */
  withoutPosition: number;
}
