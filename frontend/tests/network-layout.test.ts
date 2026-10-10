import {
  MIN_SITE_DISTANCE,
  buildNetworkLayout,
  nearestRoads,
  siteSize,
  spread,
} from "@/features/network3d/layout";
import type { MapVehicle, MapWarehouse } from "@/features/tracking/types";

const site = (id: string, lat: number, lng: number, extra: Partial<MapWarehouse> = {}) =>
  ({
    id,
    code: id.toUpperCase(),
    name: id,
    city: id,
    lat,
    lng,
    capacity: 40000,
    utilizationPct: 70,
    lowStockCount: 0,
    status: "OPERATIONAL",
    ...extra,
  }) satisfies MapWarehouse;

const vehicle = (id: string, lat: number, lng: number): MapVehicle => ({
  id,
  registration: id,
  type: "Truck",
  status: "IN_TRANSIT",
  fuelLevel: 50,
  lowFuel: false,
  lat,
  lng,
  driver: null,
  shipments: [],
});

// Garbsen and Hannover are ~9 km apart: on a country-wide board they would overlap.
const NETWORK = [
  site("ber", 52.536, 13.2),
  site("ham", 53.52, 10.0),
  site("gar", 52.422, 9.597),
  site("han", 52.4227, 9.7341),
];

const distance = (a: { x: number; z: number }, b: { x: number; z: number }) =>
  Math.hypot(a.x - b.x, a.z - b.z);

describe("network layout", () => {
  it("keeps every pair of sites far enough apart to tell them apart", () => {
    const { sites } = buildNetworkLayout(NETWORK, []);
    for (let i = 0; i < sites.length; i++) {
      for (let j = i + 1; j < sites.length; j++) {
        expect(distance(sites[i], sites[j])).toBeGreaterThanOrEqual(MIN_SITE_DISTANCE - 0.01);
      }
    }
  });

  it("keeps the geography: east is +x, north is -z", () => {
    const { sites } = buildNetworkLayout(NETWORK, []);
    const byId = Object.fromEntries(sites.map((s) => [s.id, s]));
    expect(byId.ber.x).toBeGreaterThan(byId.han.x);
    expect(byId.ham.z).toBeLessThan(byId.han.z);
  });

  it("moves a truck standing at a displaced depot together with the depot", () => {
    const { sites, vehicles } = buildNetworkLayout(NETWORK, [vehicle("v1", 52.422, 9.597)]);
    const garbsen = sites.find((s) => s.id === "gar")!;
    expect(distance(vehicles[0], garbsen)).toBeLessThan(0.01);
  });

  it("links each site to its nearest neighbours without duplicate roads", () => {
    const roads = nearestRoads([
      { id: "a", x: 0, z: 0 },
      { id: "b", x: 10, z: 0 },
      { id: "c", x: 0, z: 10 },
    ]);
    expect(roads.map((r) => r.id).sort()).toEqual(["a~b", "a~c", "b~c"]);
  });

  it("splits coincident points deterministically", () => {
    const points = [
      { x: 0, z: 0 },
      { x: 0, z: 0 },
    ];
    const first = spread(points, 5);
    expect(distance(first[0], first[1])).toBeCloseTo(5, 3);
    expect(spread(points, 5)).toEqual(first);
  });

  it("sizes buildings by capacity within a readable range", () => {
    expect(siteSize(0)).toBe(3.5);
    expect(siteSize(36000)).toBeLessThan(siteSize(60000));
    expect(siteSize(10_000_000)).toBe(6.5);
  });

  it("handles an empty network", () => {
    expect(buildNetworkLayout([], []).sites).toEqual([]);
  });
});
