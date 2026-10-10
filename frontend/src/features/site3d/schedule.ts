import type { SiteDock, SiteScene, SiteVisit } from "./model";

/** One truck's reservation of a dock: it approaches from `startMs`, is at the door from `dockedMs`. */
export interface ScheduleBlock {
  visitId: string;
  truckCode: string;
  direction: SiteVisit["direction"];
  startMs: number;
  dockedMs: number;
  endMs: number;
}

export interface DockRow {
  dock: SiteDock;
  blocks: ScheduleBlock[];
  /** "now": free at the moment; a time: when the current reservations end; null: out of service. */
  freeFrom: "now" | number | null;
  /** Start of the next reservation while the dock is free (null: nothing booked in the window). */
  nextBookingMs: number | null;
}

export interface DockSchedule {
  startMs: number;
  endMs: number;
  nowMs: number;
  rows: DockRow[];
}

export const SCHEDULE_PAST_MS = 20 * 60_000;
export const SCHEDULE_AHEAD_MS = 40 * 60_000;

/**
 * Dock availability over a window around "now", derived from the visits the scene already has
 * (no extra request). A dock is reserved from the moment its truck is due to arrive until it
 * leaves; back-to-back reservations are chained when computing when the dock is free again.
 */
export function dockSchedule(scene: SiteScene, nowMs: number): DockSchedule {
  const startMs = nowMs - SCHEDULE_PAST_MS;
  const endMs = nowMs + SCHEDULE_AHEAD_MS;
  const rows = [...scene.docks]
    .sort((a, b) => a.position - b.position)
    .map((dock): DockRow => {
      const blocks = scene.visits
        .filter((v) => v.dockCode === dock.code && v.departsMs > startMs && v.arrivesMs < endMs)
        .map((v) => ({
          visitId: v.id,
          truckCode: v.truckCode,
          direction: v.direction,
          startMs: v.arrivesMs,
          dockedMs: v.dockedMs,
          endMs: v.departsMs,
        }))
        .sort((a, b) => a.startMs - b.startMs);

      if (dock.state === "OUT_OF_SERVICE") {
        return { dock, blocks, freeFrom: null, nextBookingMs: null };
      }

      let freeFrom: DockRow["freeFrom"] = "now";
      for (const block of blocks) {
        const busyUntil = freeFrom === "now" ? nowMs : freeFrom;
        // A reservation covering "now" (or starting exactly when the previous one ends) extends it.
        if (block.startMs <= busyUntil && block.endMs > busyUntil) freeFrom = block.endMs;
      }
      const freeAt = freeFrom === "now" ? nowMs : freeFrom;
      const next = blocks.find((b) => b.startMs > freeAt);
      return {
        dock,
        blocks,
        freeFrom,
        nextBookingMs: freeFrom === "now" && next ? next.startMs : null,
      };
    });
  return { startMs, endMs, nowMs, rows };
}

/** Share (0..1) of the window at which a time sits, clamped to the window. */
export function windowShare(schedule: DockSchedule, ms: number): number {
  const share = (ms - schedule.startMs) / (schedule.endMs - schedule.startMs);
  return Math.min(1, Math.max(0, share));
}

export const clockTime = (ms: number): string =>
  new Date(ms).toLocaleTimeString("de-DE", { hour: "2-digit", minute: "2-digit" });
