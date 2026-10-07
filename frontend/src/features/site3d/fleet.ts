/**
 * Forklift traffic. Unlike trucks (whose position follows from timestamps), forklifts react to
 * what is around them, so they are a small simulation stepped every frame.
 *
 * Each working forklift cycles through its dock's routes (see `forkliftRoutes`):
 *
 *   out  -> carries a pallet from the truck to the strip exit
 *   then EITHER  trip   (to the racks beside the building and back, on the shared yard lanes)
 *        OR      local  (a short shuffle across the strip exit)
 *   back -> empty, down the return lane to the truck;  turn -> across to the out lane again
 *
 * Rules that keep the site orderly:
 *  - strips are private to one unit, so units never meet there;
 *  - the shared lanes in front of the trucks carry ONE unit at a time (a token): a unit that
 *    finds them busy does a local shuffle and tries again next lap;
 *  - a unit stops while a truck is in the way (trucks keep their schedule and never wait).
 */
import { SHARED_ZONE_Z, dockX, forkliftRoutes, type ForkliftRoutes, type Point } from "./geometry";
import type { SiteDock, SiteEquipment } from "./model";

export interface Obstacle {
  x: number;
  z: number;
  /** Heading of a model whose length runs along local +x (as for trucks). */
  heading: number;
  halfLength: number;
  halfWidth: number;
}

export interface FleetPose {
  x: number;
  z: number;
  heading: number;
  carrying: boolean;
  /** True while the unit is on the shared yard lanes. */
  onSharedLanes: boolean;
}

type Stage = "out" | "trip" | "local" | "back" | "turn";

interface Path {
  points: Point[];
  lengths: number[];
  total: number;
}

interface Unit {
  id: string;
  key: string;
  rank: number;
  paths: Record<Stage, Path>;
  dropAt: number;
  stage: Stage;
  distance: number;
  lap: number;
}

const SPEED = 4; // metres per second: brisk for a forklift, readable on screen
const PROBE_DISTANCES = [1.6, 3] as const;
const PROBE_PADDING = 0.8; // about half a forklift's width: stop before the body would touch

function makePath(points: Point[]): Path {
  const lengths = points
    .slice(1)
    .map((to, i) => Math.hypot(to.x - points[i].x, to.z - points[i].z));
  return { points, lengths, total: lengths.reduce((sum, n) => sum + n, 0) };
}

function pointAt(path: Path, distance: number): { x: number; z: number; dx: number; dz: number } {
  let remaining = Math.min(Math.max(distance, 0), path.total);
  for (let i = 0; i < path.lengths.length; i += 1) {
    const length = path.lengths[i];
    if (remaining <= length || i === path.lengths.length - 1) {
      const from = path.points[i];
      const to = path.points[i + 1];
      const t = length === 0 ? 1 : Math.min(1, remaining / length);
      return {
        x: from.x + (to.x - from.x) * t,
        z: from.z + (to.z - from.z) * t,
        dx: length === 0 ? 1 : (to.x - from.x) / length,
        dz: length === 0 ? 0 : (to.z - from.z) / length,
      };
    }
    remaining -= length;
  }
  throw new Error("path needs at least two points");
}

export function insideObstacle(x: number, z: number, o: Obstacle, padding: number): boolean {
  const dx = x - o.x;
  const dz = z - o.z;
  const cos = Math.cos(o.heading);
  const sin = Math.sin(o.heading);
  // Local +x of a model rotated by `heading` is (cos, -sin) in world (x, z); local +z is (sin, cos).
  const along = dx * cos - dz * sin;
  const across = dx * sin + dz * cos;
  return Math.abs(along) <= o.halfLength + padding && Math.abs(across) <= o.halfWidth + padding;
}

function pathsFor(routes: ForkliftRoutes): Record<Stage, Path> {
  return {
    out: makePath(routes.out),
    trip: makePath(routes.trip),
    local: makePath(routes.local),
    back: makePath(routes.back),
    turn: makePath(routes.turn),
  };
}

export class ForkliftFleet {
  private units = new Map<string, Unit>();
  private tokenHolder: string | null = null;

  /** Id of the unit currently allowed on the shared lanes, if any. */
  get lanesHeldBy(): string | null {
    return this.tokenHolder;
  }

  /**
   * Match the simulation to the scene: new working units start at their truck, units whose dock
   * changed restart there, units that stopped working disappear. Units that keep their dock keep
   * their place, so a data refresh never makes a forklift jump.
   */
  sync(equipment: SiteEquipment[], docks: SiteDock[], dockCount: number): void {
    const working = equipment
      .filter((e) => e.status === "ACTIVE" && e.assignedDockCode !== null)
      .sort((a, b) => a.code.localeCompare(b.code));
    const wanted = new Map<string, { unit: SiteEquipment; dock: SiteDock; rank: number }>();
    working.forEach((unit, rank) => {
      const dock = docks.find((d) => d.code === unit.assignedDockCode);
      if (dock) wanted.set(unit.id, { unit, dock, rank });
    });

    for (const id of [...this.units.keys()]) {
      if (!wanted.has(id)) this.remove(id);
    }
    for (const [id, { unit, dock, rank }] of wanted) {
      const key = `${dock.id}|${unit.lane}|${dockCount}`;
      const existing = this.units.get(id);
      if (existing?.key === key) {
        existing.rank = rank;
        continue;
      }
      if (existing) this.remove(id);
      const routes = forkliftRoutes(dockX(dock.position, dockCount), unit.lane, dockCount);
      const paths = pathsFor(routes);
      const dropAt = makePath(routes.trip.slice(0, routes.tripDrop + 1)).total;
      // Spread the starting points so units do not all set off in step.
      this.units.set(id, {
        id,
        key,
        rank,
        paths,
        dropAt,
        stage: "out",
        distance: (rank * 3.1) % paths.out.total,
        lap: 0,
      });
    }
  }

  private remove(id: string): void {
    this.units.delete(id);
    if (this.tokenHolder === id) this.tokenHolder = null;
  }

  has(id: string): boolean {
    return this.units.has(id);
  }

  pose(id: string): FleetPose | null {
    const unit = this.units.get(id);
    if (!unit) return null;
    const path = unit.paths[unit.stage];
    const p = pointAt(path, unit.distance);
    return {
      x: p.x,
      z: p.z,
      heading: Math.atan2(-p.dz, p.dx),
      carrying: this.carrying(unit),
      onSharedLanes: p.z > SHARED_ZONE_Z,
    };
  }

  private carrying(unit: Unit): boolean {
    switch (unit.stage) {
      case "out":
      case "local":
        return true;
      case "trip":
        return unit.distance < unit.dropAt;
      case "back":
      case "turn":
        return false;
    }
  }

  /** Advance all units by `seconds`, yielding to the given obstacles (moving trucks). */
  step(seconds: number, obstacles: readonly Obstacle[]): void {
    for (const unit of [...this.units.values()].sort((a, b) => a.rank - b.rank)) {
      if (this.blocked(unit, obstacles)) continue;
      unit.distance += SPEED * seconds;
      // A very long step may cross several stage boundaries.
      for (let guard = 0; guard < 8; guard += 1) {
        const total = unit.paths[unit.stage].total;
        if (unit.distance < total) break;
        unit.distance -= total;
        this.advanceStage(unit);
      }
    }
  }

  /** The point `ahead` metres further along the unit's route, following it into the next stage. */
  private lookahead(unit: Unit, ahead: number): { x: number; z: number } {
    const path = unit.paths[unit.stage];
    const remaining = path.total - unit.distance;
    if (ahead <= remaining) return pointAt(path, unit.distance + ahead);
    return pointAt(unit.paths[this.nextStage(unit)], ahead - remaining);
  }

  private blocked(unit: Unit, obstacles: readonly Obstacle[]): boolean {
    if (obstacles.length === 0) return false;
    return PROBE_DISTANCES.some((ahead) => {
      // Probe along the route, not in a straight line: at a corner the route turns away from
      // whatever stands in the direction the unit currently faces.
      const { x, z } = this.lookahead(unit, ahead);
      return obstacles.some((o) => insideObstacle(x, z, o, PROBE_PADDING));
    });
  }

  /** The stage that follows, without changing anything (for looking ahead). */
  private nextStage(unit: Unit): Stage {
    switch (unit.stage) {
      case "out":
        return this.wouldTakeTrip(unit) ? "trip" : "local";
      case "trip":
      case "local":
        return "back";
      case "back":
        return "turn";
      case "turn":
        return "out";
    }
  }

  private wouldTakeTrip(unit: Unit): boolean {
    const wantsTrip = (unit.lap + unit.rank) % 2 === 0;
    return wantsTrip && (this.tokenHolder === null || this.tokenHolder === unit.id);
  }

  private advanceStage(unit: Unit): void {
    switch (unit.stage) {
      case "out": {
        // At the strip exit: take a trip if the shared lanes are free and it is this unit's turn.
        if (this.wouldTakeTrip(unit)) {
          this.tokenHolder = unit.id;
          unit.stage = "trip";
        } else {
          unit.stage = "local";
        }
        return;
      }
      case "trip":
        if (this.tokenHolder === unit.id) this.tokenHolder = null;
        unit.stage = "back";
        return;
      case "local":
        unit.stage = "back";
        return;
      case "back":
        unit.stage = "turn";
        return;
      case "turn":
        unit.stage = "out";
        unit.lap += 1;
        return;
    }
  }
}
