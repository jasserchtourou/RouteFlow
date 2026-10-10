import { toSiteScene } from "@/features/site3d/mapper";
import type { SiteScene, SiteVisit } from "@/features/site3d/model";
import { dockSchedule, windowShare } from "@/features/site3d/schedule";
import { SCENE, SCENE_NOW } from "./fixtures/scene";

const MIN = 60_000;
const scene = toSiteScene(SCENE);
const row = (s: SiteScene, code: string, now = SCENE_NOW) =>
  dockSchedule(s, now).rows.find((r) => r.dock.code === code)!;

describe("dockSchedule", () => {
  it("lists the docks left to right with their reservations", () => {
    const schedule = dockSchedule(scene, SCENE_NOW);
    expect(schedule.rows.map((r) => r.dock.code)).toEqual(["In 1", "In 2", "Out 1"]);
    expect(row(scene, "Out 1").blocks).toMatchObject([
      { truckCode: "TRK-2205", startMs: SCENE_NOW - 12 * MIN, endMs: SCENE_NOW + 9 * MIN },
    ]);
  });

  it("says when a busy dock is free again", () => {
    expect(row(scene, "Out 1").freeFrom).toBe(SCENE_NOW + 9 * MIN);
    // In 1's truck is due (arrived 3 min ago), so the dock is reserved until it leaves.
    expect(row(scene, "In 1").freeFrom).toBe(SCENE_NOW + 20 * MIN);
  });

  it("marks out-of-service docks as never free", () => {
    expect(row(scene, "In 2").freeFrom).toBeNull();
  });

  it("chains back-to-back reservations", () => {
    const next: SiteVisit = {
      ...scene.visits[0],
      id: "v9",
      truckCode: "TRK-9",
      arrivesMs: SCENE_NOW + 9 * MIN,
      dockedMs: SCENE_NOW + 12 * MIN,
      departsMs: SCENE_NOW + 30 * MIN,
    };
    const busy = { ...scene, visits: [...scene.visits, next] };
    expect(row(busy, "Out 1").freeFrom).toBe(SCENE_NOW + 30 * MIN);
  });

  it("shows a free dock and when its next booking starts", () => {
    const later = SCENE_NOW + 25 * MIN; // both trucks have left
    const free = row(scene, "Out 1", later);
    expect(free.freeFrom).toBe("now");
    expect(free.nextBookingMs).toBeNull();

    const early = SCENE_NOW - 15 * MIN; // before Out 1's truck arrives
    expect(row(scene, "Out 1", early)).toMatchObject({
      freeFrom: "now",
      nextBookingMs: SCENE_NOW - 12 * MIN,
    });
  });

  it("places times on the window and clamps outside it", () => {
    const schedule = dockSchedule(scene, SCENE_NOW);
    expect(windowShare(schedule, SCENE_NOW)).toBeCloseTo(1 / 3);
    expect(windowShare(schedule, SCENE_NOW - 999 * MIN)).toBe(0);
    expect(windowShare(schedule, SCENE_NOW + 999 * MIN)).toBe(1);
  });
});
