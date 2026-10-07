import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.modules.inventory.rules import StockStatus
from app.modules.shipments.models import ShipmentStatus
from app.modules.warehouses.models import (
    DockDirection,
    EquipmentStatus,
    EquipmentType,
    WarehouseStatus,
)
from app.modules.yard.rules import DockState, VisitState


class SceneWarehouse(BaseModel):
    id: uuid.UUID
    code: str
    name: str
    location: str
    status: WarehouseStatus
    capacity: int = Field(description="Pallet positions")
    stock_pallets: int = Field(description="Occupied pallet positions")
    utilization_pct: float


class SceneKpis(BaseModel):
    stock_on_hand_pallets: int
    trucks_on_site: int = Field(description="Waiting in the yard or at a dock door")
    inbound_trucks_on_site: int
    docks_occupied: int
    docks_total: int
    on_time_rate_30d: float | None = Field(
        description="% of this site's deliveries in the last 30 days made by the promised time"
    )
    on_time_change_pts: float | None = Field(
        description="Change versus the previous 30 days, in percentage points"
    )


class SceneLayout(BaseModel):
    dock_count: int
    yard_slots: int = Field(description="Outlined waiting/staging bays in the yard")


class SceneTimings(BaseModel):
    """The yard rules' timing constants, so the client animates trucks with the same numbers
    the server uses to derive each visit's state."""

    approach_seconds: int = Field(description="Trucks are on the road this long before arriving")
    docking_seconds: int = Field(description="Reversing into the door before pallets move")
    leaving_seconds: int = Field(description="A departed truck stays visible this long")


class SceneDock(BaseModel):
    id: uuid.UUID
    code: str
    direction: DockDirection
    position: int
    state: DockState
    visit_id: uuid.UUID | None = Field(
        description="The truck at the door, or else the next one booked for it"
    )
    trucks_today: int


class SceneShipment(BaseModel):
    shipment_number: str
    destination: str
    status: ShipmentStatus
    estimated_delivery: datetime


class SceneVisit(BaseModel):
    id: uuid.UUID
    truck_code: str
    carrier: str
    direction: DockDirection
    dock_code: str
    state: VisitState
    arrives_at: datetime
    docked_at: datetime
    departs_at: datetime
    pallets_total: int
    pallets_done: int
    minutes_remaining: int | None = Field(
        description="Until the truck reaches its dock (en route/waiting) or leaves it (at the door)"
    )
    shipment: SceneShipment | None


class SceneEquipment(BaseModel):
    id: uuid.UUID
    code: str
    equipment_type: EquipmentType
    status: EquipmentStatus
    battery_level: float
    assigned_dock_code: str | None = Field(description="Dock this unit is currently serving")


class ScenePallet(BaseModel):
    id: str = Field(description="Display id, e.g. PAL-1026 (stable for a given inventory order)")
    sku: str
    product_name: str
    quantity: int
    slot: int = Field(description="Deterministic rack slot index; the client lays slots out")
    stock_status: StockStatus
    has_issue: bool = Field(description="Stock is low or out: the scene shows a pin")


class SceneRead(BaseModel):
    """Everything the 3D site view renders, in one payload: layout plus live state."""

    generated_at: datetime
    warehouse: SceneWarehouse
    kpis: SceneKpis
    layout: SceneLayout
    timings: SceneTimings
    docks: list[SceneDock]
    visits: list[SceneVisit]
    equipment: list[SceneEquipment]
    pallets: list[ScenePallet]
