import { FACADE_Z, dockX, palletPosition, type Point } from "./geometry";
import type { Selection, SiteScene, SiteVisit } from "./model";
import type { ForkliftFleet } from "./fleet";
import { parkedPose, truckPose } from "./motion";

/** The visit that belongs to a selection (a truck, or the truck at/for a dock). */
export function visitFor(scene: SiteScene, selection: Selection | null): SiteVisit | undefined {
  if (!selection) return undefined;
  if (selection.kind === "truck") return scene.visits.find((v) => v.id === selection.id);
  if (selection.kind === "dock") {
    const dock = scene.docks.find((d) => d.id === selection.id);
    return dock?.visitId ? scene.visits.find((v) => v.id === dock.visitId) : undefined;
  }
  return undefined;
}

/** Visit shown in the shipment tracker: the selected one, else whatever is being worked on. */
export function trackedVisit(scene: SiteScene, selection: Selection | null): SiteVisit | undefined {
  return (
    visitFor(scene, selection) ??
    scene.visits.find((v) => v.state === "LOADING" || v.state === "UNLOADING") ??
    scene.visits[0]
  );
}

/** Ground position of a selection (for focusing the camera), or null when it no longer exists. */
export function selectionPoint(
  scene: SiteScene,
  selection: Selection,
  nowMs: number,
  fleet?: ForkliftFleet,
): Point | null {
  switch (selection.kind) {
    case "dock": {
      const dock = scene.docks.find((d) => d.id === selection.id);
      return dock ? { x: dockX(dock.position, scene.dockCount), z: FACADE_Z + 4 } : null;
    }
    case "truck": {
      const visit = scene.visits.find((v) => v.id === selection.id);
      const dock = visit && scene.docks.find((d) => d.code === visit.dockCode);
      if (!visit || !dock) return null;
      return truckPose(visit, dock, scene.dockCount, scene.timings, nowMs);
    }
    case "forklift": {
      const unit = scene.equipment.find((e) => e.id === selection.id);
      if (!unit) return null;
      return fleet?.pose(unit.id) ?? parkedPose(unit, scene.dockCount);
    }
    case "pallet": {
      const pallet = scene.pallets.find((p) => p.id === selection.id);
      if (!pallet) return null;
      const { x, z } = palletPosition(pallet.slot, scene.dockCount);
      return { x, z };
    }
  }
}

/** Whether the selected object is still part of the scene (a truck may have driven away). */
export function selectionExists(scene: SiteScene, selection: Selection): boolean {
  switch (selection.kind) {
    case "dock":
      return scene.docks.some((d) => d.id === selection.id);
    case "truck":
      return scene.visits.some((v) => v.id === selection.id);
    case "forklift":
      return scene.equipment.some((e) => e.id === selection.id);
    case "pallet":
      return scene.pallets.some((p) => p.id === selection.id);
  }
}
