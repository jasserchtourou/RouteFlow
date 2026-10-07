import {
  BAY_Z,
  DOCKED_Z,
  DOCK_SPACING,
  ROAD_END_X,
  ROAD_Z,
  bayPoint,
  buildingWidth,
  dockX,
  dockedPoint,
  palletPosition,
} from "@/features/site3d/geometry";
import { toSiteScene } from "@/features/site3d/mapper";
import {
  headingOf,
  parkedPose,
  poseAlong,
  truckObstacles,
  truckPose,
} from "@/features/site3d/motion";
import {
  selectionExists,
  selectionPoint,
  trackedVisit,
  visitFor,
} from "@/features/site3d/selection";
import { SCENE, SCENE_NOW } from "./fixtures/scene";

const scene = toSiteScene(SCENE);
const MIN = 60_000;
const [loading, waiting] = scene.visits;
const dockOf = (code: string) => scene.docks.find((d) => d.code === code)!;

describe("geometry", () => {
  it("spreads docks symmetrically along the facade", () => {
    expect(dockX(1, 3)).toBeCloseTo(-DOCK_SPACING);
    expect(dockX(2, 3)).toBeCloseTo(0);
    expect(dockX(3, 3)).toBeCloseTo(DOCK_SPACING);
    expect(buildingWidth(3)).toBeCloseTo(3 * DOCK_SPACING + 4);
  });

  it("parks trucks in bays on alternating sides of the dock corridor", () => {
    const left = bayPoint(0, 3);
    const right = bayPoint(1, 3);
    expect(left.x).toBeLessThan(-1.5 * DOCK_SPACING);
    expect(right.x).toBeGreaterThan(1.5 * DOCK_SPACING);
    expect(bayPoint(2, 3).x).toBeLessThan(left.x);
  });

  it("lays pallets out in racks without overlap", () => {
    const seen = new Set<string>();
    for (let slot = 0; slot < 48; slot += 1) {
      const p = palletPosition(slot, 3);
      seen.add(`${p.x}/${p.y}/${p.z}`);
    }
    expect(seen.size).toBe(48);
  });
});

describe("poseAlong", () => {
  const segments = [
    { from: { x: 0, z: 0 }, to: { x: 10, z: 0 }, reverse: false },
    { from: { x: 10, z: 0 }, to: { x: 10, z: -10 }, reverse: true },
  ];

  it("interpolates by distance across segments", () => {
    expect(poseAlong(segments, 0)).toMatchObject({ x: 0, z: 0 });
    expect(poseAlong(segments, 0.25)).toMatchObject({ x: 5, z: 0 });
    expect(poseAlong(segments, 0.75)).toMatchObject({ x: 10, z: -5 });
    expect(poseAlong(segments, 1)).toMatchObject({ x: 10, z: -10 });
  });

  it("faces the direction of travel, and away from it when reversing", () => {
    expect(poseAlong(segments, 0.25).heading).toBeCloseTo(headingOf(1, 0));
    // Moving towards -z in reverse means the front points to +z.
    expect(poseAlong(segments, 0.75).heading).toBeCloseTo(headingOf(0, 1));
  });
});

describe("truckPose", () => {
  const T = scene.timings;
  const at = (v: typeof loading, ms: number) =>
    truckPose(v, dockOf(v.dockCode), scene.dockCount, T, SCENE_NOW + ms);

  it("is invisible before the approach and after leaving", () => {
    expect(at(waiting, -3 * MIN - T.approachMs - 1)).toBeNull();
    expect(at(waiting, 20 * MIN + T.leavingMs)).toBeNull();
  });

  it("starts at the road edge and ends in its bay when the truck arrives", () => {
    const start = at(waiting, -3 * MIN - T.approachMs)!;
    expect(start).toMatchObject({ x: -ROAD_END_X, z: ROAD_Z });
    const bay = bayPoint(waiting.bay, scene.dockCount);
    expect(at(waiting, -3 * MIN)).toMatchObject({ x: bay.x, z: BAY_Z });
    expect(at(waiting, 0)).toMatchObject({ x: bay.x, z: BAY_Z }); // waiting for the dock
  });

  it("is backed into the dock while pallets move, facing the yard", () => {
    const pose = at(loading, 0)!;
    const door = dockedPoint(dockOf("Out 1").position, scene.dockCount);
    expect(pose).toMatchObject({ x: door.x, z: DOCKED_Z });
    expect(pose.heading).toBeCloseTo(headingOf(0, 1));
  });

  it("drives away along the road after departing", () => {
    const early = at(loading, 9 * MIN + 1000)!;
    const late = at(loading, 9 * MIN + T.leavingMs - 1000)!;
    expect(early.z).toBeGreaterThan(DOCKED_Z - 0.01);
    expect(late.z).toBeCloseTo(ROAD_Z, 0);
    expect(late.x).toBeGreaterThan(early.x);
  });

  it("moves continuously (no jumps between consecutive moments)", () => {
    let previous = at(waiting, 3 * MIN)!;
    for (let ms = 3 * MIN + 1000; ms < 3 * MIN + T.dockingMs; ms += 1000) {
      const pose = at(waiting, ms)!;
      expect(Math.hypot(pose.x - previous.x, pose.z - previous.z)).toBeLessThan(3);
      previous = pose;
    }
  });
});

describe("parkedPose", () => {
  it("keeps units that are not working at their depot spot", () => {
    const [, broken, idle] = scene.equipment;
    for (const unit of [broken, idle]) {
      const pose = parkedPose(unit, scene.dockCount);
      expect(pose.working).toBe(false);
      expect(pose.carrying).toBe(false);
    }
  });
});

describe("truckObstacles", () => {
  it("lists the trucks that are on screen", () => {
    const t = scene.timings;
    const now = truckObstacles(scene.visits, scene.docks, scene.dockCount, t, SCENE_NOW);
    expect(now).toHaveLength(2);
    const later = truckObstacles(
      scene.visits,
      scene.docks,
      scene.dockCount,
      t,
      SCENE_NOW + 60 * MIN,
    );
    expect(later).toHaveLength(0);
  });
});

describe("toSiteScene", () => {
  it("converts timestamps and gives each visit its own yard bay", () => {
    expect(scene.generatedMs).toBe(SCENE_NOW);
    expect(loading.arrivesMs).toBe(SCENE_NOW - 12 * MIN);
    expect(scene.timings.dockingMs).toBe(60_000);
    expect(new Set(scene.visits.map((v) => v.bay)).size).toBe(scene.visits.length);
  });

  it("numbers equipment within each status for separate parking spots", () => {
    expect(scene.equipment.map((e) => [e.code, e.slot])).toEqual([
      ["FL-01", 0],
      ["FL-02", 0],
      ["RT-01", 0],
    ]);
  });

  it("gives forklifts serving the same dock separate lanes", () => {
    const raw = {
      ...SCENE,
      equipment: SCENE.equipment.map((e) => ({
        ...e,
        status: "ACTIVE" as const,
        assigned_dock_code: "Out 1",
      })),
    };
    expect(toSiteScene(raw).equipment.map((e) => e.lane)).toEqual([0, 1, 2]);
  });
});

describe("selection helpers", () => {
  it("finds the visit for a truck or a dock selection", () => {
    expect(visitFor(scene, { kind: "truck", id: "v1" })?.truckCode).toBe("TRK-2205");
    expect(visitFor(scene, { kind: "dock", id: "d1" })?.truckCode).toBe("TRK-2481");
    expect(visitFor(scene, { kind: "dock", id: "d2" })).toBeUndefined();
    expect(visitFor(scene, { kind: "pallet", id: "PAL-1001" })).toBeUndefined();
    expect(visitFor(scene, null)).toBeUndefined();
  });

  it("tracks the truck being worked on when nothing is selected", () => {
    expect(trackedVisit(scene, null)?.truckCode).toBe("TRK-2205");
    expect(trackedVisit(scene, { kind: "truck", id: "v2" })?.truckCode).toBe("TRK-2481");
  });

  it("knows whether the selected object still exists", () => {
    expect(selectionExists(scene, { kind: "truck", id: "v1" })).toBe(true);
    expect(selectionExists(scene, { kind: "truck", id: "gone" })).toBe(false);
    expect(selectionExists(scene, { kind: "dock", id: "d3" })).toBe(true);
    expect(selectionExists(scene, { kind: "forklift", id: "e9" })).toBe(false);
    expect(selectionExists(scene, { kind: "pallet", id: "PAL-1002" })).toBe(true);
  });

  it("gives a ground point to focus the camera on", () => {
    const dock = selectionPoint(scene, { kind: "dock", id: "d3" }, SCENE_NOW)!;
    expect(dock.x).toBeCloseTo(dockX(3, 3));
    expect(selectionPoint(scene, { kind: "truck", id: "v1" }, SCENE_NOW)).not.toBeNull();
    expect(selectionPoint(scene, { kind: "forklift", id: "e1" }, SCENE_NOW)).not.toBeNull();
    expect(selectionPoint(scene, { kind: "pallet", id: "PAL-1001" }, SCENE_NOW)).not.toBeNull();
    expect(selectionPoint(scene, { kind: "pallet", id: "nope" }, SCENE_NOW)).toBeNull();
    expect(selectionPoint(scene, { kind: "dock", id: "nope" }, SCENE_NOW)).toBeNull();
    expect(selectionPoint(scene, { kind: "truck", id: "nope" }, SCENE_NOW)).toBeNull();
    expect(selectionPoint(scene, { kind: "forklift", id: "nope" }, SCENE_NOW)).toBeNull();
  });
});
