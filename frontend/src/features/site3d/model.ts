/** View-model of the site scene: camelCase, timestamps as epoch milliseconds. */
import type {
  DockDirection,
  DockState,
  EquipmentStatus,
  StockStatus,
  VisitState,
} from "./api-types";

export interface SiteDock {
  id: string;
  code: string;
  direction: DockDirection;
  position: number;
  state: DockState;
  visitId: string | null;
  trucksToday: number;
}

export interface SiteShipment {
  number: string;
  destination: string;
  status: string;
  etaMs: number;
}

export interface SiteVisit {
  id: string;
  truckCode: string;
  carrier: string;
  direction: DockDirection;
  dockCode: string;
  state: VisitState;
  arrivesMs: number;
  dockedMs: number;
  departsMs: number;
  palletsTotal: number;
  palletsDone: number;
  minutesRemaining: number | null;
  shipment: SiteShipment | null;
  /** Index of the yard bay this truck waits in (stable per visit within a scene). */
  bay: number;
}

export interface SiteEquipment {
  id: string;
  code: string;
  type: string;
  status: EquipmentStatus;
  battery: number;
  assignedDockCode: string | null;
  /** Position among equipment with the same status; used to give each unit its own parking spot. */
  slot: number;
  /** Index among the units serving the same dock; picks the forklift's own lane. */
  lane: number;
}

export interface SitePallet {
  id: string;
  sku: string;
  name: string;
  quantity: number;
  slot: number;
  stockStatus: StockStatus;
  hasIssue: boolean;
}

export interface Timings {
  approachMs: number;
  dockingMs: number;
  leavingMs: number;
}

export interface SiteScene {
  generatedMs: number;
  warehouse: {
    id: string;
    code: string;
    name: string;
    location: string;
    capacity: number;
    stockPallets: number;
    utilizationPct: number;
  };
  kpis: {
    stockOnHand: number;
    trucksOnSite: number;
    inboundOnSite: number;
    docksOccupied: number;
    docksTotal: number;
    onTimeRate: number | null;
    onTimeChangePts: number | null;
  };
  dockCount: number;
  yardSlots: number;
  timings: Timings;
  docks: SiteDock[];
  visits: SiteVisit[];
  equipment: SiteEquipment[];
  pallets: SitePallet[];
}

/** What the user can select in the scene or the operations list. */
export type Selection =
  | { kind: "dock"; id: string }
  | { kind: "truck"; id: string }
  | { kind: "forklift"; id: string }
  | { kind: "pallet"; id: string };
