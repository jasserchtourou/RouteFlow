import type { SceneResponse } from "./api-types";
import type { SiteScene } from "./model";

const ms = (iso: string): number => new Date(iso).getTime();

export function toSiteScene(scene: SceneResponse): SiteScene {
  // Each truck waiting in the yard gets its own bay: visits are numbered by arrival order and
  // wrapped over the available bays, so two trucks never share one unless the yard is over-full.
  const bays = Math.max(1, scene.layout.yard_slots);
  const byArrival = [...scene.visits].sort((a, b) => ms(a.arrives_at) - ms(b.arrives_at));
  const bayOf = new Map(byArrival.map((visit, index) => [visit.id, index % bays]));

  const seen: Record<string, number> = {};
  const perDock: Record<string, number> = {};
  return {
    generatedMs: ms(scene.generated_at),
    warehouse: {
      id: scene.warehouse.id,
      code: scene.warehouse.code,
      name: scene.warehouse.name,
      location: scene.warehouse.location,
      capacity: scene.warehouse.capacity,
      stockPallets: scene.warehouse.stock_pallets,
      utilizationPct: scene.warehouse.utilization_pct,
    },
    kpis: {
      stockOnHand: scene.kpis.stock_on_hand_pallets,
      trucksOnSite: scene.kpis.trucks_on_site,
      inboundOnSite: scene.kpis.inbound_trucks_on_site,
      docksOccupied: scene.kpis.docks_occupied,
      docksTotal: scene.kpis.docks_total,
      onTimeRate: scene.kpis.on_time_rate_30d,
      onTimeChangePts: scene.kpis.on_time_change_pts,
    },
    dockCount: scene.layout.dock_count,
    yardSlots: scene.layout.yard_slots,
    timings: {
      approachMs: scene.timings.approach_seconds * 1000,
      dockingMs: scene.timings.docking_seconds * 1000,
      leavingMs: scene.timings.leaving_seconds * 1000,
    },
    docks: scene.docks.map((d) => ({
      id: d.id,
      code: d.code,
      direction: d.direction,
      position: d.position,
      state: d.state,
      visitId: d.visit_id,
      trucksToday: d.trucks_today,
    })),
    visits: scene.visits.map((v) => ({
      id: v.id,
      truckCode: v.truck_code,
      carrier: v.carrier,
      direction: v.direction,
      dockCode: v.dock_code,
      state: v.state,
      arrivesMs: ms(v.arrives_at),
      dockedMs: ms(v.docked_at),
      departsMs: ms(v.departs_at),
      palletsTotal: v.pallets_total,
      palletsDone: v.pallets_done,
      minutesRemaining: v.minutes_remaining,
      shipment: v.shipment && {
        number: v.shipment.shipment_number,
        destination: v.shipment.destination,
        status: v.shipment.status,
        etaMs: ms(v.shipment.estimated_delivery),
      },
      bay: bayOf.get(v.id) ?? 0,
    })),
    equipment: scene.equipment.map((e) => {
      const slot = seen[e.status] ?? 0;
      seen[e.status] = slot + 1;
      const dock = e.assigned_dock_code ?? "";
      const lane = perDock[dock] ?? 0;
      perDock[dock] = lane + 1;
      return {
        id: e.id,
        code: e.code,
        type: e.equipment_type,
        status: e.status,
        battery: e.battery_level,
        assignedDockCode: e.assigned_dock_code,
        slot,
        lane,
      };
    }),
    pallets: scene.pallets.map((p) => ({
      id: p.id,
      sku: p.sku,
      name: p.product_name,
      quantity: p.quantity,
      slot: p.slot,
      stockStatus: p.stock_status,
      hasIssue: p.has_issue,
    })),
  };
}
