/**
 * World layout of the site. Units are metres, +x to the right, +z towards the viewer (the yard),
 * -z into the building. Everything is derived from the dock/bay counts the backend reports, so
 * no coordinates are stored anywhere.
 */

export interface Point {
  x: number;
  z: number;
}

// Wide enough that each truck has a forklift work strip on both sides.
export const DOCK_SPACING = 8.4;
export const BUILDING_DEPTH = 14;
export const BUILDING_HEIGHT = 6;
export const FACADE_Z = -2; // front wall of the building
export const TRUCK_LENGTH = 9.2;
export const TRUCK_WIDTH = 2.6;
export const DOCKED_Z = FACADE_Z + TRUCK_LENGTH / 2 + 0.5; // truck centre when backed in
export const BAY_Z = 12.5; // centre of the waiting bays
export const ROAD_Z = 23; // centre line of the road
export const ROAD_HALF_WIDTH = 4;
export const ROAD_END_X = 46;
export const BAY_SPACING = 5;
export const RACK_ORIGIN: Point = { x: 0, z: -9 }; // offset from the right edge of the building

/** Half of the width taken by the dock doors. */
export function dockSpan(dockCount: number): number {
  return (Math.max(1, dockCount) * DOCK_SPACING) / 2;
}

export function buildingWidth(dockCount: number): number {
  return dockSpan(dockCount) * 2 + 4;
}

/** X of a dock door; `position` is 1-based, left to right along the facade. */
export function dockX(position: number, dockCount: number): number {
  return (position - (dockCount + 1) / 2) * DOCK_SPACING;
}

/** Where a truck's centre stops when backed into a dock. */
export function dockedPoint(position: number, dockCount: number): Point {
  return { x: dockX(position, dockCount), z: DOCKED_Z };
}

/**
 * Waiting bays sit to the left and right of the dock corridor (trucks reversing into a door
 * need the straight lane in front of the doors), alternating sides outwards.
 */
export function bayPoint(bay: number, dockCount: number): Point {
  const side = bay % 2 === 0 ? -1 : 1;
  const ring = Math.floor(bay / 2);
  return { x: side * (dockSpan(dockCount) + 9 + ring * BAY_SPACING), z: BAY_Z };
}

/** How far the paved yard reaches to each side. */
export function yardHalfWidth(dockCount: number, yardSlots: number): number {
  return dockSpan(dockCount) + 9 + Math.ceil(yardSlots / 2) * BAY_SPACING + 6;
}

/** Rack position for the n-th pallet: 6 per row, 2 levels, aisles stepping away from the facade. */
export function palletPosition(
  slot: number,
  dockCount: number,
): { x: number; y: number; z: number } {
  const perRow = 6;
  const levels = 2;
  const column = slot % perRow;
  const level = Math.floor(slot / perRow) % levels;
  const aisle = Math.floor(slot / (perRow * levels));
  const rightEdge = buildingWidth(dockCount) / 2;
  return {
    x: rightEdge + 7 + column * 1.5,
    y: 0.45 + level * 1.6,
    z: RACK_ORIGIN.z + aisle * 3.2,
  };
}

/** Parking spots for equipment that is not working: depot (idle), chargers, workshop. */
export function equipmentHome(
  status: "ACTIVE" | "IDLE" | "CHARGING" | "MAINTENANCE",
  slot: number,
  dockCount: number,
): Point {
  const leftEdge = -buildingWidth(dockCount) / 2;
  const row = slot * 2.2;
  switch (status) {
    case "CHARGING":
      return { x: leftEdge - 6, z: 1 + row };
    case "MAINTENANCE":
      return { x: leftEdge - 10, z: 1 + row };
    case "IDLE":
    case "ACTIVE":
      return { x: leftEdge - 3, z: 1 + row };
  }
}

export const FORKLIFTS_PER_DOCK = 2; // keep equal to the backend's MAX_FORKLIFTS_PER_DOCK
const LOOP_HALF_WIDTH = 0.45; // the out lane and the return lane are 0.9 m apart
/** Where a dock's strips end and the shared yard lanes begin. Strips are private to one unit. */
export const EXIT_Z = 6.5;
/** Shared one-way lanes in front of the trucks: loaded units go right, empty ones come back. */
export const LOADED_LANE_Z = 11;
export const EMPTY_LANE_Z = 9.6;
/** Rack road columns beside the building: loaded units drive up one, empty ones down the other. */
export const RACK_DROP_Z = RACK_ORIGIN.z + 1;
/** The shared lanes start below this line (used to check that only one unit is out there). */
export const SHARED_ZONE_Z = EXIT_Z + 1.5;

export interface ForkliftRoutes {
  /** Door end -> strip exit, carrying the pallet picked up at the truck. */
  out: Point[];
  /** Strip exit -> racks -> strip exit: only while the shared lanes are free. */
  trip: Point[];
  /** Index in `trip` of the point where the pallet is put down (at the racks). */
  tripDrop: number;
  /** Strip exit -> across to the return lane: the short local shuffle instead of a trip. */
  local: Point[];
  /** Strip exit -> door end, empty. */
  back: Point[];
  /** Across the door end to the out lane again. */
  turn: Point[];
}

/**
 * The paths of a forklift working one dock. Every dock owns two strips, one either side of its
 * truck; a unit gets one of them (by its index among the units serving that dock). Strips of
 * different units never overlap and stay clear of the trailers; the shared lanes in front of
 * the trucks are used by one unit at a time (see `ForkliftFleet`).
 */
export function forkliftRoutes(
  dockXValue: number,
  lane: number,
  dockCount: number,
): ForkliftRoutes {
  const side = lane % FORKLIFTS_PER_DOCK === 0 ? -1 : 1;
  const stripCentre = dockXValue + side * (TRUCK_WIDTH / 2 + (DOCK_SPACING - TRUCK_WIDTH) / 4);
  const out = stripCentre - LOOP_HALF_WIDTH;
  const back = stripCentre + LOOP_HALF_WIDTH;
  const door = FACADE_Z + 2;
  const edge = buildingWidth(dockCount) / 2;
  const rackLoaded = edge + 3;
  const rackEmpty = edge + 4.3;
  return {
    out: [
      { x: out, z: door },
      { x: out, z: EXIT_Z },
    ],
    trip: [
      { x: out, z: EXIT_Z },
      { x: out, z: LOADED_LANE_Z },
      { x: rackLoaded, z: LOADED_LANE_Z },
      { x: rackLoaded, z: RACK_DROP_Z },
      { x: rackEmpty, z: RACK_DROP_Z },
      { x: rackEmpty, z: EMPTY_LANE_Z },
      { x: back, z: EMPTY_LANE_Z },
      { x: back, z: EXIT_Z },
    ],
    tripDrop: 3,
    local: [
      { x: out, z: EXIT_Z },
      { x: back, z: EXIT_Z },
    ],
    back: [
      { x: back, z: EXIT_Z },
      { x: back, z: door },
    ],
    turn: [
      { x: back, z: door },
      { x: out, z: door },
    ],
  };
}
