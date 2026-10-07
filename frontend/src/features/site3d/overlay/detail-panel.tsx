"use client";

import { Info, X } from "lucide-react";
import type { ReactNode } from "react";
import { Badge, type Tone } from "@/components/ui/badge";
import { Panel } from "@/components/ui/panel";
import { formatPercent } from "@/lib/format";
import { humanize } from "@/features/tracking/mappers";
import type { Selection, SiteScene } from "../model";

const DOCK_TONE: Record<string, Tone> = {
  AVAILABLE: "success",
  BOOKED: "warning",
  OCCUPIED: "danger",
  OUT_OF_SERVICE: "neutral",
};

const VISIT_TONE: Record<string, Tone> = {
  EN_ROUTE: "info",
  WAITING: "warning",
  DOCKED: "info",
  LOADING: "success",
  UNLOADING: "success",
  DEPARTED: "neutral",
};

const STOCK_TONE: Record<string, Tone> = { OK: "success", LOW: "warning", OUT_OF_STOCK: "danger" };

function Row({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-4 border-b border-border/60 py-1.5 text-sm last:border-0">
      <dt className="text-muted">{label}</dt>
      <dd className="text-right font-medium">{value}</dd>
    </div>
  );
}

function Frame({
  kind,
  title,
  subtitle,
  badge,
  onClose,
  children,
}: {
  kind: string;
  title: string;
  subtitle: string;
  badge: ReactNode;
  onClose: () => void;
  children: ReactNode;
}) {
  return (
    <Panel
      id="detail"
      label={`${kind} details`}
      title={title}
      icon={Info}
      summary={kind}
      actions={
        <button
          type="button"
          onClick={onClose}
          aria-label="Close details"
          className="grid size-8 shrink-0 place-items-center rounded-lg text-muted hover:bg-surface-hover hover:text-foreground"
        >
          <X aria-hidden className="size-4" />
        </button>
      }
    >
      <p className="text-[11px] font-semibold uppercase tracking-wide text-accent">{kind}</p>
      <p className="truncate text-xs text-muted">{subtitle}</p>
      <div className="my-3">{badge}</div>
      <dl>{children}</dl>
    </Panel>
  );
}

export function DetailPanel({
  scene,
  selection,
  onClose,
}: {
  scene: SiteScene;
  selection: Selection;
  onClose: () => void;
}) {
  const site = scene.warehouse.name;

  if (selection.kind === "dock") {
    const dock = scene.docks.find((d) => d.id === selection.id);
    if (!dock) return null;
    const visit = scene.visits.find((v) => v.id === dock.visitId);
    return (
      <Frame
        kind={`Dock bay · ${scene.warehouse.code}`}
        title={dock.code}
        subtitle={`${humanize(dock.direction)} dock door`}
        badge={
          <span className="flex items-center gap-2">
            <Badge tone={DOCK_TONE[dock.state]}>{humanize(dock.state)}</Badge>
            {visit?.minutesRemaining != null && (
              <span className="text-xs text-muted">
                {visit.truckCode}{" "}
                {visit.state === "EN_ROUTE" || visit.state === "WAITING" ? "due in" : "leaves in"}{" "}
                {visit.minutesRemaining} min
              </span>
            )}
          </span>
        }
        onClose={onClose}
      >
        <Row label="Truck" value={visit ? `${visit.truckCode} · ${visit.carrier}` : "—"} />
        <Row label="Pallets" value={visit ? `${visit.palletsDone}/${visit.palletsTotal}` : "—"} />
        <Row label="Trucks today" value={dock.trucksToday} />
        <Row label="Site" value={site} />
      </Frame>
    );
  }

  if (selection.kind === "truck") {
    const visit = scene.visits.find((v) => v.id === selection.id);
    if (!visit) return null;
    return (
      <Frame
        kind="Truck"
        title={visit.truckCode}
        subtitle={visit.carrier}
        badge={<Badge tone={VISIT_TONE[visit.state]}>{humanize(visit.state)}</Badge>}
        onClose={onClose}
      >
        <Row label="Dock" value={visit.dockCode} />
        <Row label="Direction" value={humanize(visit.direction)} />
        <Row label="Pallets" value={`${visit.palletsDone}/${visit.palletsTotal}`} />
        <Row label="Shipment" value={visit.shipment?.number ?? "—"} />
        <Row
          label="Time"
          value={visit.minutesRemaining === null ? "—" : `${visit.minutesRemaining} min`}
        />
        <Row label="Site" value={site} />
      </Frame>
    );
  }

  if (selection.kind === "forklift") {
    const unit = scene.equipment.find((e) => e.id === selection.id);
    if (!unit) return null;
    return (
      <Frame
        kind={humanize(unit.type)}
        title={unit.code}
        subtitle={site}
        badge={
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
        }
        onClose={onClose}
      >
        <Row label="Battery" value={formatPercent(unit.battery, 0)} />
        <Row label="Serving dock" value={unit.assignedDockCode ?? "—"} />
        <Row label="Site" value={site} />
      </Frame>
    );
  }

  const pallet = scene.pallets.find((p) => p.id === selection.id);
  if (!pallet) return null;
  return (
    <Frame
      kind={`Pallet · ${pallet.sku}`}
      title={pallet.name}
      subtitle={pallet.id}
      badge={<Badge tone={STOCK_TONE[pallet.stockStatus]}>{humanize(pallet.stockStatus)}</Badge>}
      onClose={onClose}
    >
      <Row label="Quantity" value={`${pallet.quantity} units`} />
      <Row label="Location" value={`${scene.warehouse.code} · Rack slot ${pallet.slot + 1}`} />
      <Row label="SKU" value={pallet.sku} />
      <Row label="Site" value={site} />
      {pallet.hasIssue && (
        <p className="mt-3 rounded-lg bg-warning/10 p-2 text-xs text-warning">
          Stock is at or below its reorder threshold.
        </p>
      )}
    </Frame>
  );
}
