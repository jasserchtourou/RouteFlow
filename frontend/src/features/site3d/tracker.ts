import type { SiteVisit } from "./model";

export interface TrackerStep {
  label: string;
  /** Extra line under the label (progress or ETA). */
  detail?: string;
  status: "done" | "active" | "todo";
}

/**
 * The stepper for the selected truck. Steps follow the truck's visit (what is physically
 * happening at the site), so the stepper never contradicts the 3D scene.
 */
export function trackerSteps(visit: SiteVisit): TrackerStep[] {
  const progress = `${visit.palletsDone}/${visit.palletsTotal}`;
  const left = visit.state === "DEPARTED";

  let labels: string[];
  let active: number;
  if (visit.direction === "OUTBOUND") {
    labels = ["Order confirmed", "Picked", `Loading ${progress}`, "In transit", "Delivered"];
    active = left ? 3 : visit.state === "LOADING" ? 2 : 1;
  } else {
    labels = ["En route", "In yard", `Unloading ${progress}`, "Put away"];
    active = left ? 3 : visit.state === "UNLOADING" ? 2 : visit.state === "EN_ROUTE" ? 0 : 1;
  }

  return labels.map((label, index) => ({
    label,
    status: index < active ? "done" : index === active ? "active" : "todo",
    detail:
      visit.direction === "OUTBOUND" && index === 4 && visit.shipment
        ? `ETA ${new Date(visit.shipment.etaMs).toLocaleTimeString("de-DE", { hour: "2-digit", minute: "2-digit" })}`
        : undefined,
  }));
}
