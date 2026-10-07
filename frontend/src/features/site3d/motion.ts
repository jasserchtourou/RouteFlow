/**
 * Where things are at a given moment. The backend only says *when* a truck arrives, docks and
 * leaves; these pure functions turn those timestamps into positions, so motion is smooth between
 * the 5-second data refreshes and always matches the server's idea of each visit's state.
 */
import type { Obstacle } from "./fleet";
import {
  BAY_Z,
  ROAD_END_X,
  ROAD_Z,
  bayPoint,
  dockedPoint,
  equipmentHome,
  TRUCK_LENGTH,
  TRUCK_WIDTH,
  type Point,
} from "./geometry";
import type { SiteDock, SiteEquipment, SiteVisit, Timings } from "./model";

export interface Pose {
  x: number;
  z: number;
  /** Rotation about the vertical axis (radians) for a model whose front points along +x. */
  heading: number;
}

interface Segment {
  from: Point;
  to: Point;
  /** Driving backwards: the truck faces away from its direction of travel. */
  reverse: boolean;
}

/** Heading that makes a +x-facing model look along (dx, dz). */
export function headingOf(dx: number, dz: number): number {
  return Math.atan2(-dz, dx);
}

const smoothstep = (p: number): number => p * p * (3 - 2 * p);
const clamp01 = (p: number): number => Math.min(1, Math.max(0, p));

function length(segment: Segment): number {
  return Math.hypot(segment.to.x - segment.from.x, segment.to.z - segment.from.z);
}

/** Pose after travelling the fraction `p` (0..1) of the whole polyline. */
export function poseAlong(segments: Segment[], p: number): Pose {
  const total = segments.reduce((sum, s) => sum + length(s), 0);
  let remaining = clamp01(p) * total;
  for (const segment of segments) {
    const len = length(segment);
    if (remaining <= len || segment === segments[segments.length - 1]) {
      const t = len === 0 ? 1 : Math.min(1, remaining / len);
      const dx = segment.to.x - segment.from.x;
      const dz = segment.to.z - segment.from.z;
      const sign = segment.reverse ? -1 : 1;
      return {
        x: segment.from.x + dx * t,
        z: segment.from.z + dz * t,
        heading: headingOf(sign * dx, sign * dz),
      };
    }
    remaining -= len;
  }
  throw new Error("poseAlong needs at least one segment");
}

const roadStart: Point = { x: -ROAD_END_X, z: ROAD_Z };
const roadEnd: Point = { x: ROAD_END_X, z: ROAD_Z };

/** Truck pose for `nowMs`, or null when the truck is not on the site's screen. */
export function truckPose(
  visit: SiteVisit,
  dock: SiteDock,
  dockCount: number,
  timings: Timings,
  nowMs: number,
): Pose | null {
  const bay = bayPoint(visit.bay, dockCount);
  const door = dockedPoint(dock.position, dockCount);
  const bayRoad: Point = { x: bay.x, z: ROAD_Z };
  const doorRoad: Point = { x: door.x, z: ROAD_Z };

  const arriveStart = visit.arrivesMs - timings.approachMs;
  const dockEnd = visit.dockedMs + timings.dockingMs;
  const leaveEnd = visit.departsMs + timings.leavingMs;
  if (nowMs < arriveStart || nowMs >= leaveEnd) return null;

  if (nowMs < visit.arrivesMs) {
    // Drive along the road, then reverse into the waiting bay.
    return poseAlong(
      [
        { from: roadStart, to: bayRoad, reverse: false },
        { from: bayRoad, to: { x: bay.x, z: BAY_Z }, reverse: true },
      ],
      smoothstep((nowMs - arriveStart) / timings.approachMs),
    );
  }
  if (nowMs < visit.dockedMs) {
    return { x: bay.x, z: BAY_Z, heading: headingOf(0, 1) };
  }
  if (nowMs < dockEnd) {
    // Pull out of the bay, drive to the right door and reverse in.
    return poseAlong(
      [
        { from: { x: bay.x, z: BAY_Z }, to: bayRoad, reverse: false },
        { from: bayRoad, to: doorRoad, reverse: false },
        { from: doorRoad, to: door, reverse: true },
      ],
      smoothstep((nowMs - visit.dockedMs) / timings.dockingMs),
    );
  }
  if (nowMs < visit.departsMs) {
    return { x: door.x, z: door.z, heading: headingOf(0, 1) };
  }
  // Drive forward out of the door and away along the road.
  return poseAlong(
    [
      { from: door, to: doorRoad, reverse: false },
      { from: doorRoad, to: roadEnd, reverse: false },
    ],
    smoothstep((nowMs - visit.departsMs) / timings.leavingMs),
  );
}

export interface ForkliftPose extends Pose {
  carrying: boolean;
  working: boolean;
}

/** Where a forklift that is not working stands: the depot, chargers or workshop. */
export function parkedPose(unit: SiteEquipment, dockCount: number): ForkliftPose {
  const home = equipmentHome(unit.status, unit.slot, dockCount);
  return { ...home, heading: headingOf(1, 0), carrying: false, working: false };
}

/**
 * Moving trucks (and parked ones) as obstacles forklifts must give way to. Trucks follow their
 * schedule and never wait, so it is always the forklift that stops.
 */
export function truckObstacles(
  visits: SiteVisit[],
  docks: SiteDock[],
  dockCount: number,
  timings: Timings,
  nowMs: number,
): Obstacle[] {
  const obstacles: Obstacle[] = [];
  for (const visit of visits) {
    const dock = docks.find((d) => d.code === visit.dockCode);
    const pose = dock && truckPose(visit, dock, dockCount, timings, nowMs);
    if (pose) {
      obstacles.push({
        x: pose.x,
        z: pose.z,
        heading: pose.heading,
        halfLength: TRUCK_LENGTH / 2 + 0.1,
        halfWidth: TRUCK_WIDTH / 2,
      });
    }
  }
  return obstacles;
}
