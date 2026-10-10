import type { VehicleResponse, WarehouseMapResponse } from "./api-types";
import { VEHICLE_STATUSES, type FleetMapData, type MapVehicle, type VehicleStatus } from "./types";

/** "REFRIGERATED_TRUCK" -> "Refrigerated truck". */
export function humanize(value: string): string {
  const text = value.toLowerCase().replaceAll("_", " ");
  return text.charAt(0).toUpperCase() + text.slice(1);
}

function isVehicleStatus(value: string): value is VehicleStatus {
  return (VEHICLE_STATUSES as readonly string[]).includes(value);
}

export function toMapVehicle(vehicle: VehicleResponse): MapVehicle | null {
  // A vehicle that never reported a position cannot be drawn.
  if (!vehicle.position || !isVehicleStatus(vehicle.status)) return null;
  return {
    id: vehicle.id,
    registration: vehicle.registration,
    type: humanize(vehicle.vehicle_type),
    status: vehicle.status,
    fuelLevel: vehicle.fuel_level,
    lowFuel: vehicle.low_fuel,
    lat: vehicle.position.latitude,
    lng: vehicle.position.longitude,
    driver: vehicle.driver_name,
    shipments: vehicle.active_shipments,
  };
}

export function toFleetMapData(
  vehicles: VehicleResponse[],
  warehouses: WarehouseMapResponse[],
): FleetMapData {
  const mapped = vehicles.map(toMapVehicle);
  const drawable = mapped.filter((v): v is MapVehicle => v !== null);
  // In-transit vehicles first, then by registration: the list reads like a dispatch board.
  const rank = (status: VehicleStatus) => VEHICLE_STATUSES.indexOf(status);
  drawable.sort(
    (a, b) => rank(a.status) - rank(b.status) || a.registration.localeCompare(b.registration),
  );
  return {
    vehicles: drawable,
    warehouses: warehouses.map((w) => ({
      id: w.id,
      code: w.code,
      name: w.name,
      city: w.location,
      lat: w.latitude,
      lng: w.longitude,
      capacity: w.capacity,
      utilizationPct: Math.round(w.utilization_pct),
      lowStockCount: w.low_stock_count,
      status: w.status,
    })),
    withoutPosition: vehicles.length - drawable.length,
  };
}
