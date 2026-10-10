/**
 * Board layout of the network view. Sites and vehicles are placed by their real coordinates on a
 * flat "game board" (units are scene units, +x east, -z north). Sites that are too close to be
 * told apart (e.g. two depots in the same city) are pushed apart; vehicles near a moved site move
 * with it, so a truck at a depot still stands next to that depot.
 */
import type { MapVehicle, MapWarehouse } from "@/features/tracking/types";

export interface BoardPoint {
  x: number;
  z: number;
}

export interface BoardSite extends MapWarehouse, BoardPoint {
  /** Side length of the building footprint, from the site's capacity. */
  size: number;
}

export interface BoardVehicle extends MapVehicle, BoardPoint {}

export interface BoardRoad {
  id: string;
  from: BoardPoint;
  to: BoardPoint;
}

export interface NetworkLayout {
  sites: BoardSite[];
  vehicles: BoardVehicle[];
  roads: BoardRoad[];
  /** Half the board size; the board is centred on the origin. */
  halfWidth: number;
  halfDepth: number;
}

/** Usable board area: the network is scaled to fit into this rectangle. */
const FIT_WIDTH = 56;
const FIT_DEPTH = 34;
/** Minimum distance between two site centres (a building plus room for its label). */
export const MIN_SITE_DISTANCE = 12;
const MARGIN = 9;

/** Building side from capacity: area grows with capacity, clamped to a readable range. */
export function siteSize(capacity: number): number {
  return Math.min(6.5, Math.max(3.5, Math.sqrt(Math.max(0, capacity)) / 38));
}

/** Equirectangular projection around the network's centre (fine at country scale). */
function projector(points: { lat: number; lng: number }[]) {
  const lats = points.map((p) => p.lat);
  const lngs = points.map((p) => p.lng);
  const midLat = (Math.min(...lats) + Math.max(...lats)) / 2;
  const midLng = (Math.min(...lngs) + Math.max(...lngs)) / 2;
  const k = Math.cos((midLat * Math.PI) / 180);
  const raw = (lat: number, lng: number): BoardPoint => ({
    x: (lng - midLng) * k,
    z: -(lat - midLat),
  });
  const spanX = Math.max(1e-6, ...points.map((p) => Math.abs(raw(p.lat, p.lng).x) * 2));
  const spanZ = Math.max(1e-6, ...points.map((p) => Math.abs(raw(p.lat, p.lng).z) * 2));
  const scale = Math.min(FIT_WIDTH / spanX, FIT_DEPTH / spanZ);
  return (lat: number, lng: number): BoardPoint => {
    const p = raw(lat, lng);
    return { x: p.x * scale, z: p.z * scale };
  };
}

/**
 * Pushes points apart until no two are closer than `minDistance`. Deterministic: coincident
 * points are split along a fixed direction that depends on their order.
 */
export function spread(points: BoardPoint[], minDistance: number): BoardPoint[] {
  const out = points.map((p) => ({ ...p }));
  for (let iteration = 0; iteration < 80; iteration++) {
    let moved = false;
    for (let i = 0; i < out.length; i++) {
      for (let j = i + 1; j < out.length; j++) {
        let dx = out[j].x - out[i].x;
        let dz = out[j].z - out[i].z;
        let distance = Math.hypot(dx, dz);
        if (distance >= minDistance - 1e-6) continue;
        if (distance < 1e-6) {
          const angle = (j * 2.399) % (Math.PI * 2); // golden angle: no two pairs share a direction
          dx = Math.cos(angle);
          dz = Math.sin(angle);
          distance = 1;
        }
        const push = (minDistance - Math.hypot(out[j].x - out[i].x, out[j].z - out[i].z)) / 2;
        const ux = dx / distance;
        const uz = dz / distance;
        out[i].x -= ux * push;
        out[i].z -= uz * push;
        out[j].x += ux * push;
        out[j].z += uz * push;
        moved = true;
      }
    }
    if (!moved) break;
  }
  return out;
}

/** Each site is linked to its two nearest neighbours; duplicates are dropped. */
export function nearestRoads(sites: (BoardPoint & { id: string })[]): BoardRoad[] {
  const seen = new Set<string>();
  const roads: BoardRoad[] = [];
  for (const site of sites) {
    const nearest = sites
      .filter((other) => other.id !== site.id)
      .map((other) => ({ other, d: Math.hypot(other.x - site.x, other.z - site.z) }))
      .sort((a, b) => a.d - b.d)
      .slice(0, 2);
    for (const { other } of nearest) {
      const id = [site.id, other.id].sort().join("~");
      if (seen.has(id)) continue;
      seen.add(id);
      roads.push({ id, from: { x: site.x, z: site.z }, to: { x: other.x, z: other.z } });
    }
  }
  return roads;
}

export function buildNetworkLayout(
  warehouses: MapWarehouse[],
  vehicles: MapVehicle[],
): NetworkLayout {
  const all = [...warehouses, ...vehicles];
  if (all.length === 0) {
    return { sites: [], vehicles: [], roads: [], halfWidth: 20, halfDepth: 14 };
  }
  const project = projector(all);
  const projected = warehouses.map((w) => project(w.lat, w.lng));
  const placed = spread(projected, MIN_SITE_DISTANCE);
  const sites: BoardSite[] = warehouses.map((w, i) => ({
    ...w,
    ...placed[i],
    size: siteSize(w.capacity),
  }));

  // A vehicle follows the displacement of a site it is close to, fading out with distance.
  const reach = MIN_SITE_DISTANCE * 1.2;
  const boardVehicles: BoardVehicle[] = vehicles.map((v) => {
    const p = project(v.lat, v.lng);
    let dx = 0;
    let dz = 0;
    let best = Infinity;
    projected.forEach((origin, i) => {
      const d = Math.hypot(p.x - origin.x, p.z - origin.z);
      if (d < best && d < reach) {
        best = d;
        const weight = 1 - d / reach;
        dx = (placed[i].x - origin.x) * weight;
        dz = (placed[i].z - origin.z) * weight;
      }
    });
    return { ...v, x: p.x + dx, z: p.z + dz };
  });

  const xs = [...sites.map((s) => s.x), ...boardVehicles.map((v) => v.x)];
  const zs = [...sites.map((s) => s.z), ...boardVehicles.map((v) => v.z)];
  return {
    sites,
    vehicles: boardVehicles,
    roads: nearestRoads(sites),
    halfWidth: Math.max(...xs.map(Math.abs)) + MARGIN,
    halfDepth: Math.max(...zs.map(Math.abs)) + MARGIN,
  };
}

/** Colour key for a site's status beacon (shared by the scene and its legend). */
export const STATUS_COLOR: Record<MapWarehouse["status"], string> = {
  OPERATIONAL: "#34d399",
  CONGESTED: "#fbbf24",
  DISRUPTED: "#f87171",
  OFFLINE: "#64708f",
};

/** Same thresholds as the rest of the app (HIGH >= 85 %, CRITICAL >= 95 %). */
export function utilizationColor(pct: number): string {
  if (pct >= 95) return "#f87171";
  if (pct >= 85) return "#fbbf24";
  return "#4f8cff";
}
