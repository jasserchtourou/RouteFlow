import { toSiteScene } from "@/features/site3d/mapper";
import { trackerSteps } from "@/features/site3d/tracker";
import { SCENE } from "./fixtures/scene";

const scene = toSiteScene(SCENE);
const [outbound, inbound] = scene.visits;

const statuses = (steps: ReturnType<typeof trackerSteps>) => steps.map((s) => s.status);

describe("trackerSteps", () => {
  it("shows loading progress for a truck being loaded", () => {
    const steps = trackerSteps(outbound);
    expect(steps.map((s) => s.label)).toEqual([
      "Order confirmed",
      "Picked",
      "Loading 2/6",
      "In transit",
      "Delivered",
    ]);
    expect(statuses(steps)).toEqual(["done", "done", "active", "todo", "todo"]);
    expect(steps[4].detail).toMatch(/^ETA \d\d:\d\d$/);
  });

  it("moves to 'in transit' once the truck has left", () => {
    const steps = trackerSteps({ ...outbound, state: "DEPARTED" });
    expect(statuses(steps)).toEqual(["done", "done", "done", "active", "todo"]);
  });

  it("waits at 'picked' while an outbound truck is still arriving or docking", () => {
    expect(statuses(trackerSteps({ ...outbound, state: "WAITING" }))).toEqual([
      "done",
      "active",
      "todo",
      "todo",
      "todo",
    ]);
  });

  it("uses an inbound sequence for trucks that deliver to the site", () => {
    expect(statuses(trackerSteps({ ...inbound, state: "EN_ROUTE" }))).toEqual([
      "active",
      "todo",
      "todo",
      "todo",
    ]);
    expect(statuses(trackerSteps(inbound))).toEqual(["done", "active", "todo", "todo"]);
    const unloading = trackerSteps({ ...inbound, state: "UNLOADING", palletsDone: 5 });
    expect(unloading[2].label).toBe("Unloading 5/12");
    expect(statuses(unloading)).toEqual(["done", "done", "active", "todo"]);
    expect(statuses(trackerSteps({ ...inbound, state: "DEPARTED" }))).toEqual([
      "done",
      "done",
      "done",
      "active",
    ]);
  });
});
