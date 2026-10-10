"use client";

import { cn } from "@/lib/utils";
import type { Selection, SiteScene } from "../model";
import { isSame } from "../scene/interaction";
import { clockTime, dockSchedule, windowShare, type DockRow } from "../schedule";

const TICK_MS = 15 * 60_000;

function FreeText({ row }: { row: DockRow }) {
  if (row.freeFrom === null) return <span className="text-muted">Out of service</span>;
  if (row.freeFrom === "now") {
    return (
      <span className="text-success">
        Free
        {row.nextBookingMs !== null && (
          <span className="text-muted"> · until {clockTime(row.nextBookingMs)}</span>
        )}
      </span>
    );
  }
  return <span className="text-warning">Free {clockTime(row.freeFrom)}</span>;
}

/**
 * Dock availability timeline: one track per door, a bar per truck reservation (light part:
 * approaching, solid part: at the door), and a line for "now". Bars are buttons that select the
 * truck in the scene.
 */
export function DockSchedule({
  scene,
  nowMs,
  selection,
  onSelect,
}: {
  scene: SiteScene;
  nowMs: number;
  selection: Selection | null;
  onSelect: (selection: Selection) => void;
}) {
  const schedule = dockSchedule(scene, nowMs);
  const pct = (ms: number) => `${windowShare(schedule, ms) * 100}%`;
  const firstTick = Math.ceil(schedule.startMs / TICK_MS) * TICK_MS;
  const ticks = Array.from(
    { length: Math.floor((schedule.endMs - firstTick) / TICK_MS) + 1 },
    (_, i) => firstTick + i * TICK_MS,
  );
  const freeNow = schedule.rows.filter((r) => r.freeFrom === "now").length;

  return (
    <div className="flex flex-col gap-1.5">
      <p className="px-1 text-xs text-muted">
        <span className="font-medium text-foreground">{freeNow}</span> of {schedule.rows.length}{" "}
        docks free now
        <span className="ml-2 inline-flex items-center gap-1">
          <span aria-hidden className="h-2 w-3 rounded-sm bg-accent" /> inbound
        </span>
        <span className="ml-2 inline-flex items-center gap-1">
          <span aria-hidden className="h-2 w-3 rounded-sm bg-warning" /> outbound
        </span>
      </p>

      {/* Time axis */}
      <div className="flex items-end gap-2 px-1">
        <span className="w-12 shrink-0" />
        <div aria-hidden className="relative h-4 flex-1">
          {ticks.map((t) => (
            <span
              key={t}
              className="absolute -translate-x-1/2 text-[10px] tabular-nums text-muted"
              style={{ left: pct(t) }}
            >
              {clockTime(t)}
            </span>
          ))}
        </div>
        <span className="w-24 shrink-0" />
      </div>

      <ul aria-label="Dock schedule" className="flex flex-col gap-1">
        {schedule.rows.map((row) => (
          <li key={row.dock.id} className="flex items-center gap-2 px-1 text-xs">
            <span className="w-12 shrink-0 font-medium">{row.dock.code}</span>
            <div
              className={cn(
                "relative h-5 flex-1 overflow-hidden rounded bg-background/70",
                row.freeFrom === null &&
                  "bg-[repeating-linear-gradient(135deg,transparent_0_5px,rgba(141,154,184,0.18)_5px_10px)]",
              )}
            >
              {ticks.map((t) => (
                <span
                  key={t}
                  aria-hidden
                  className="absolute inset-y-0 w-px bg-border/60"
                  style={{ left: pct(t) }}
                />
              ))}
              {row.blocks.map((block) => {
                const target = { kind: "truck", id: block.visitId } as const;
                const selected = isSame(selection, target);
                const solid = block.direction === "INBOUND" ? "bg-accent" : "bg-warning";
                const left = windowShare(schedule, block.startMs);
                const docked = windowShare(schedule, block.dockedMs);
                const right = windowShare(schedule, block.endMs);
                return (
                  <button
                    key={block.visitId}
                    type="button"
                    onClick={() => onSelect(target)}
                    aria-pressed={selected}
                    aria-label={`${block.truckCode} at ${row.dock.code}, ${clockTime(block.startMs)} to ${clockTime(block.endMs)}`}
                    title={`${block.truckCode} · arrives ${clockTime(block.startMs)} · at door ${clockTime(block.dockedMs)} · leaves ${clockTime(block.endMs)}`}
                    className={cn(
                      "absolute inset-y-0.5 flex overflow-hidden rounded-sm transition-[filter] hover:brightness-125",
                      selected && "ring-2 ring-foreground",
                    )}
                    style={{
                      left: `${left * 100}%`,
                      width: `${Math.max(0.01, right - left) * 100}%`,
                    }}
                  >
                    <span
                      className={cn("h-full opacity-40", solid)}
                      style={{
                        width: `${right > left ? ((docked - left) / (right - left)) * 100 : 0}%`,
                      }}
                    />
                    <span
                      className={cn("flex h-full flex-1 items-center overflow-hidden px-1", solid)}
                    >
                      <span className="truncate text-[10px] font-semibold text-accent-fg">
                        {block.truckCode}
                      </span>
                    </span>
                  </button>
                );
              })}
              <span
                aria-hidden
                className="absolute inset-y-0 w-0.5 bg-foreground shadow-[0_0_6px_rgba(255,255,255,0.6)]"
                style={{ left: pct(schedule.nowMs) }}
              />
            </div>
            <span className="w-24 shrink-0 truncate text-right">
              <FreeText row={row} />
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
