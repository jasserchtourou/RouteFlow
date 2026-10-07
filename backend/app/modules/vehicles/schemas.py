import uuid
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from app.core.pagination import PageParams
from app.core.types import SearchTerm
from app.modules.drivers.models import DriverStatus
from app.modules.vehicles.models import VehicleStatus, VehicleType


class Position(BaseModel):
    latitude: float
    longitude: float


class VehicleRead(BaseModel):
    id: uuid.UUID
    registration: str
    vehicle_type: VehicleType
    status: VehicleStatus
    fuel_level: float
    low_fuel: bool
    position: Position | None = Field(description="Last reported (simulated) GPS position")
    driver_id: uuid.UUID | None
    driver_name: str | None
    active_shipments: list[str] = Field(description="Shipment numbers on board, by ETA")
    updated_at: datetime


class VehicleSort(StrEnum):
    REGISTRATION = "registration"
    FUEL = "fuel"  # emptiest first


class VehicleListParams(PageParams):
    model_config = ConfigDict(extra="forbid")

    status: list[VehicleStatus] | None = Field(default=None, description="Repeatable")
    vehicle_type: list[VehicleType] | None = Field(default=None, description="Repeatable")
    low_fuel: bool | None = None
    search: SearchTerm | None = Field(default=None, description="Registration")
    sort: VehicleSort = VehicleSort.REGISTRATION


class FleetOverview(BaseModel):
    total: int
    by_status: dict[VehicleStatus, int]
    by_type: dict[VehicleType, int]
    operational: int = Field(description="AVAILABLE + IN_TRANSIT")
    utilization_pct: float | None = Field(description="IN_TRANSIT share of operational vehicles")
    low_fuel: int
    drivers_by_status: dict[DriverStatus, int]
