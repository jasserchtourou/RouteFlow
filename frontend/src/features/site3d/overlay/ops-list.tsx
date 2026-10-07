"use client";

import { ChevronRight, ListChecks } from "lucide-react";
import { useState } from "react";
import { Badge, type Tone } from "@/components/ui/badge";
import { Panel } from "@/components/ui/panel";
import { humanize } from "@/features/tracking/mappers";
import { cn } from "@/lib/utils";
import type { Selection, SiteScene } from "../model";
import { isSame } from "../scene/interaction";
import { NIGHT } from "../scene/palette";

type Tab = "docks" | "forklifts" | "trucks";

const DOCK_TONE: Record<string, Tone> = {
  AVAILABLE: "success",
  BOOKED: "warning",
  OCCUPIED: "danger",
  OUT_OF_SERVICE: "neutral",
};

const LEGEND = [
  ["AVAILABLE", "Available"],
  ["BOOKED", "Booked"],
  ["OCCUPIED", "Occupied"],
  ["OUT_OF_SERVICE", "Out of service"],
] as const;

function Progress({ done, total }: { done: number; total: number }) {
  const pct = total === 0 ? 0 : Math.round((done / total) * 100);
  return (
    <span className="flex items-center gap-2 text-xs tabular-nums text-muted">
      <span
        role="progressbar"
        aria-label="Pallets moved"
        aria-valuenow={done}
        aria-valuemin={0}
        aria-valuemax={total}
        className="h-1.5 w-12 overflow-hidden rounded-full bg-surface-hover"
      >
        <span className="block h-full rounded-full bg-success" style={{ width: `${pct}%` }} />
      </span>
      {done}/{total}
    </span>
  );
}

function Row({
  selected,
  onClick,
  children,
}: {
  selected: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <li>
      <button
        type="button"
        onClick={onClick}
        aria-pressed={selected}
        className={cn(
          "flex w-full items-center gap-3 rounded-lg px-2 py-2 text-left text-sm transition-colors hover:bg-surface-hover",
          selected && "bg-accent/10",
        )}
      >
        {children}
        <ChevronRight aria-hidden className="ml-auto size-4 shrink-0 text-muted" />
      </button>
    </li>
  );
}

export function OpsList({
  scene,
  selection,
  onSelect,
}: {
  scene: SiteScene;
  selection: Selection | null;
  onSelect: (selection: Selection) => void;
}) {
  const [tab, setTab] = useState<Tab>("docks");
  const activeUnits = scene.equipment.filter((e) => e.status === "ACTIVE").length;
  const tabs: { id: Tab; label: string; count: string }[] = [
    { id: "docks", label: "Docks", count: `${scene.kpis.docksOccupied}/${scene.kpis.docksTotal}` },
    { id: "forklifts", label: "Forklifts", count: `${activeUnits}/${scene.equipment.length}` },
    { id: "trucks", label: "Trucks", count: String(scene.visits.length) },
  ];
  const summary = tabs.map((t) => `${t.count} ${t.label.toLowerCase()}`).join(" · ");

  return (
    <Panel id="ops" label="Site operations" title="Operations" icon={ListChecks} summary={summary}>
      <div className="mb-2 flex items-center justify-between gap-2">
        <div
          role="tablist"
          aria-label="Operations"
          className="flex gap-1 rounded-lg bg-background/70 p-1"
        >
          {tabs.map((t) => (
            <button
              key={t.id}
              role="tab"
              type="button"
              aria-selected={tab === t.id}
              onClick={() => setTab(t.id)}
              className={cn(
                "rounded-md px-2.5 py-1 text-xs font-medium transition-colors",
                tab === t.id
                  ? "bg-surface text-foreground shadow"
                  : "text-muted hover:text-foreground",
              )}
            >
              {t.label} <span className="text-accent">{t.count}</span>
            </button>
          ))}
        </div>
        <span className="truncate text-xs text-muted">{scene.warehouse.name}</span>
      </div>

      {tab === "docks" && (
        <ul
          aria-label="Dock colours"
          className="mb-2 flex flex-wrap gap-x-3 gap-y-1 px-1 text-[11px] text-muted"
        >
          {LEGEND.map(([state, label]) => (
            <li key={state} className="flex items-center gap-1.5">
              <span
                aria-hidden
                className="size-2 rounded-full"
                style={{ background: NIGHT.doorState[state] }}
              />
              {label}
            </li>
          ))}
        </ul>
      )}

      <ul role="tabpanel" className="max-h-[min(13rem,26vh)] overflow-y-auto">
        {tab === "docks" &&
          scene.docks.map((dock) => {
            const visit = scene.visits.find((v) => v.id === dock.visitId);
            const target = { kind: "dock", id: dock.id } as const;
            return (
              <Row
                key={dock.id}
                selected={isSame(selection, target)}
                onClick={() => onSelect(target)}
              >
                <span className="w-12 shrink-0 font-medium">{dock.code}</span>
                <span className="min-w-0 flex-1 truncate text-muted">
                  {visit ? `${visit.truckCode} · ${visit.carrier}` : "No truck assigned"}
                </span>
                <Badge tone={DOCK_TONE[dock.state]}>
                  {visit && dock.state === "OCCUPIED"
                    ? humanize(visit.state)
                    : humanize(dock.state)}
                </Badge>
                {visit && (visit.state === "LOADING" || visit.state === "UNLOADING") && (
                  <Progress done={visit.palletsDone} total={visit.palletsTotal} />
                )}
              </Row>
            );
          })}

        {tab === "forklifts" &&
          scene.equipment.map((unit) => {
            const target = { kind: "forklift", id: unit.id } as const;
            return (
              <Row
                key={unit.id}
                selected={isSame(selection, target)}
                onClick={() => onSelect(target)}
              >
                <span className="w-14 shrink-0 font-medium">{unit.code}</span>
                <span className="min-w-0 flex-1 truncate text-muted">
                  {unit.assignedDockCode ? `Serving ${unit.assignedDockCode}` : humanize(unit.type)}
                </span>
                <Badge
                  tone={
                    unit.status === "ACTIVE"
                      ? "success"
                      : unit.status === "MAINTENANCE"
                        ? "warning"
                        : "neutral"
                  }
                >
                  {humanize(unit.status)}
                </Badge>
                <span className="w-9 text-right text-xs tabular-nums text-muted">
                  {Math.round(unit.battery)}%
                </span>
              </Row>
            );
          })}

        {tab === "trucks" &&
          (scene.visits.length === 0 ? (
            <li className="px-2 py-3 text-sm text-muted">No trucks on site or arriving.</li>
          ) : (
            scene.visits.map((visit) => {
              const target = { kind: "truck", id: visit.id } as const;
              return (
                <Row
                  key={visit.id}
                  selected={isSame(selection, target)}
                  onClick={() => onSelect(target)}
                >
                  <span className="w-20 shrink-0 font-mono font-medium">{visit.truckCode}</span>
                  <span className="min-w-0 flex-1 truncate text-muted">
                    {visit.carrier} · {visit.dockCode}
                  </span>
                  <Badge
                    tone={
                      visit.state === "LOADING" || visit.state === "UNLOADING"
                        ? "success"
                        : visit.state === "WAITING"
                          ? "warning"
                          : "info"
                    }
                  >
                    {humanize(visit.state)}
                  </Badge>
                  {visit.minutesRemaining !== null && (
                    <span className="w-12 text-right text-xs tabular-nums text-muted">
                      {visit.minutesRemaining} min
                    </span>
                  )}
                </Row>
              );
            })
          ))}
      </ul>
    </Panel>
  );
}
