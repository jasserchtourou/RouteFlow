import type { VehicleResponse, WarehouseMapResponse } from "@/features/tracking/api-types";

export const VEHICLES: VehicleResponse[] = [
  {
    id: "v1",
    registration: "B-RF 1259",
    vehicle_type: "SEMI_TRAILER",
    status: "AVAILABLE",
    fuel_level: 80,
    low_fuel: false,
    position: { latitude: 51.8, longitude: 12.7 },
    driver_name: "Aylin Demir",
    active_shipments: [],
  },
  {
    id: "v2",
    registration: "B-RF 1074",
    vehicle_type: "TRUCK",
    status: "IN_TRANSIT",
    fuel_level: 12.4,
    low_fuel: true,
    position: { latitude: 52.39, longitude: 9.69 },
    driver_name: "Murat Yilmaz",
    active_shipments: ["SHP-2254", "SHP-2245"],
  },
  {
    id: "v3",
    registration: "B-RF 1444",
    vehicle_type: "REFRIGERATED_TRUCK",
    status: "MAINTENANCE",
    fuel_level: 50,
    low_fuel: false,
    position: null,
    driver_name: null,
    active_shipments: [],
  },
];

export const WAREHOUSES: WarehouseMapResponse[] = [
  {
    id: "w1",
    code: "WH-GAR",
    name: "Garbsen Logistics Park",
    location: "Garbsen",
    latitude: 52.42,
    longitude: 9.6,
    utilization_pct: 96.2,
    status: "DISRUPTED",
  },
];
