import {
  DOCK_SPACING,
  DOCKED_Z,
  EXIT_Z,
  RACK_DROP_Z,
  TRUCK_LENGTH,
  TRUCK_WIDTH,
  buildingWidth,
  dockX,
} from "@/features/site3d/geometry";
import { ForkliftFleet, insideObstacle, type Obstacle } from "@/features/site3d/fleet";
import type { SiteDock, SiteEquipment } from "@/features/site3d/model";

const DT = 0.05;

function site(dockCount: number, perDock = 2) {
  const docks: SiteDock[] = Array.from({ length: dockCount }, (_, i) => ({
    id: `d${i + 1}`,
    code: `Dock ${i + 1}`,
    direction: i % 2 === 0 ? "INBOUND" : "OUTBOUND",
    position: i + 1,
    state: "OCCUPIED",
    visitId: null,
    trucksToday: 0,
  }));
  const equipment: SiteEquipment[] = docks.flatMap((dock, d) =>
    Array.from({ length: perDock }, (_, lane) => ({
      id: `f${d}-${lane}`,
      code: `FL-${String(d * perDock + lane + 1).padStart(2, "0")}`,
      type: "FORKLIFT",
      status: "ACTIVE" as const,
      battery: 80,
      assignedDockCode: dock.code,
      slot: d * perDock + lane,
      lane,
    })),
  );
  return { docks, equipment, dockCount };
}

/** A truck backed into every dock: they stand beside the forklift strips all the time. */
function dockedTrucks(dockCount: number): Obstacle[] {
  return Array.from({ length: dockCount }, (_, i) => ({
    x: dockX(i + 1, dockCount),
    z: DOCKED_Z,
    heading: -Math.PI / 2, // facing the yard
    halfLength: TRUCK_LENGTH / 2 + 0.1,
    halfWidth: TRUCK_WIDTH / 2,
  }));
}

interface Run {
  minDistance: number;
  maxOnLanes: number;
  trailerHits: number;
  travelled: Map<string, number>;
  reachedRacks: Set<string>;
  carriedAtRacks: boolean;
  droppedAfterRacks: boolean;
  tokenGrants: number;
}

function simulate(
  fleet: ForkliftFleet,
  ids: string[],
  seconds: number,
  obstacles: Obstacle[] | ((t: number) => Obstacle[]),
  trailers: Obstacle[] = [],
  rackX = Infinity,
): Run {
  const run: Run = {
    minDistance: Infinity,
    maxOnLanes: 0,
    trailerHits: 0,
    travelled: new Map(ids.map((id) => [id, 0])),
    reachedRacks: new Set(),
    carriedAtRacks: false,
    droppedAfterRacks: false,
    tokenGrants: 0,
  };
  let last = new Map(ids.map((id) => [id, fleet.pose(id)!]));
  let holder = fleet.lanesHeldBy;
  for (let t = 0; t < seconds; t += DT) {
    fleet.step(DT, typeof obstacles === "function" ? obstacles(t) : obstacles);
    const poses = ids.map((id) => ({ id, pose: fleet.pose(id)! }));
    run.maxOnLanes = Math.max(run.maxOnLanes, poses.filter((p) => p.pose.onSharedLanes).length);
    for (const { id, pose } of poses) {
      const before = last.get(id)!;
      run.travelled.set(
        id,
        run.travelled.get(id)! + Math.hypot(pose.x - before.x, pose.z - before.z),
      );
      if (trailers.some((o) => insideObstacle(pose.x, pose.z, o, 0.75))) run.trailerHits += 1;
      if (pose.x >= rackX && pose.z <= RACK_DROP_Z + 0.3) {
        run.reachedRacks.add(id);
        if (pose.carrying) run.carriedAtRacks = true;
        else run.droppedAfterRacks = true;
      }
    }
    for (let i = 0; i < poses.length; i += 1) {
      for (let j = i + 1; j < poses.length; j += 1) {
        run.minDistance = Math.min(
          run.minDistance,
          Math.hypot(poses[i].pose.x - poses[j].pose.x, poses[i].pose.z - poses[j].pose.z),
        );
      }
    }
    if (fleet.lanesHeldBy !== null && fleet.lanesHeldBy !== holder) run.tokenGrants += 1;
    holder = fleet.lanesHeldBy;
    last = new Map(poses.map((p) => [p.id, p.pose]));
  }
  return run;
}

describe("ForkliftFleet on a busy site (7 docks, 14 forklifts)", () => {
  const { docks, equipment, dockCount } = site(7);
  const ids = equipment.map((e) => e.id);
  const trucks = dockedTrucks(dockCount);
  const rackX = buildingWidth(dockCount) / 2 + 2.5;
  const fleet = new ForkliftFleet();
  fleet.sync(equipment, docks, dockCount);
  const run = simulate(fleet, ids, 900, trucks, trucks, rackX);

  it("never lets two forklifts touch or cross", () => {
    // Bodies are about 1.5 m wide; units in neighbouring strips are 2.0 m apart at the closest.
    expect(run.minDistance).toBeGreaterThanOrEqual(1.9);
  });

  it("never drives through a docked trailer", () => {
    expect(run.trailerHits).toBe(0);
  });

  it("lets only one forklift use the shared yard lanes at a time, in turns", () => {
    expect(run.maxOnLanes).toBeLessThanOrEqual(1);
    expect(run.tokenGrants).toBeGreaterThan(10);
  });

  it("takes pallets all the way to the racks, carrying them there and dropping them", () => {
    expect(run.reachedRacks.size).toBeGreaterThan(5);
    expect(run.carriedAtRacks).toBe(true);
    expect(run.droppedAfterRacks).toBe(true);
  });

  it("keeps every forklift busy, also while the lanes are taken", () => {
    for (const [id, metres] of run.travelled) {
      expect(metres, `${id} barely moved`).toBeGreaterThan(300);
    }
  });
});

describe("ForkliftFleet and trucks", () => {
  it("stops in front of a truck that blocks its way and carries on once it has gone", () => {
    const { docks, equipment, dockCount } = site(3, 1);
    const fleet = new ForkliftFleet();
    fleet.sync(equipment, docks, dockCount);
    const ids = equipment.map((e) => e.id);
    // A truck parked across the loaded lane, to the right of every strip.
    const blocker: Obstacle = {
      x: buildingWidth(dockCount) / 2 - 1,
      z: 11,
      heading: 0,
      halfLength: 4.7,
      halfWidth: 1.3,
    };
    const run = simulate(fleet, ids, 200, [blocker], [blocker]);
    expect(run.trailerHits).toBe(0); // nobody drove into the truck
    // The unit holding the lanes waits for the truck; the others keep working locally.
    expect(fleet.lanesHeldBy).not.toBeNull();
    const working = ids.filter((id) => fleet.pose(id)!.z < EXIT_Z + 0.1);
    expect(working.length).toBeGreaterThanOrEqual(2);

    const after = simulate(fleet, ids, 120, [], [], buildingWidth(dockCount) / 2 + 2.5);
    expect(after.reachedRacks.size).toBeGreaterThan(0);
  });
});

describe("ForkliftFleet.sync", () => {
  it("only simulates active units that are assigned to a dock", () => {
    const { docks, equipment, dockCount } = site(2, 1);
    const mixed: SiteEquipment[] = [
      equipment[0],
      { ...equipment[1], status: "IDLE", assignedDockCode: null },
    ];
    const fleet = new ForkliftFleet();
    fleet.sync(mixed, docks, dockCount);
    expect(fleet.has(equipment[0].id)).toBe(true);
    expect(fleet.has(equipment[1].id)).toBe(false);
    expect(fleet.pose(equipment[1].id)).toBeNull();
  });

  it("keeps a unit in place across refreshes but restarts it when its dock changes", () => {
    const { docks, equipment, dockCount } = site(3, 1);
    const fleet = new ForkliftFleet();
    fleet.sync(equipment, docks, dockCount);
    for (let i = 0; i < 100; i += 1) fleet.step(DT, []);
    const moved = fleet.pose(equipment[0].id)!;

    fleet.sync(equipment, docks, dockCount); // refresh with the same assignment
    expect(fleet.pose(equipment[0].id)).toEqual(moved);

    const reassigned = equipment.map((e, i) =>
      i === 0 ? { ...e, assignedDockCode: docks[2].code } : e,
    );
    fleet.sync(reassigned, docks, dockCount);
    const restarted = fleet.pose(equipment[0].id)!;
    expect(restarted.x).toBeGreaterThan(dockX(3, dockCount) - DOCK_SPACING);
    expect(restarted).not.toEqual(moved);
  });

  it("frees the shared lanes when the unit holding them is removed", () => {
    const { docks, equipment, dockCount } = site(3, 1);
    const fleet = new ForkliftFleet();
    fleet.sync(equipment, docks, dockCount);
    let holder: string | null = null;
    for (let i = 0; i < 2000 && holder === null; i += 1) {
      fleet.step(DT, []);
      holder = fleet.lanesHeldBy;
    }
    expect(holder).not.toBeNull();
    fleet.sync(
      equipment.filter((e) => e.id !== holder),
      docks,
      dockCount,
    );
    expect(fleet.lanesHeldBy).toBeNull();
  });
});
