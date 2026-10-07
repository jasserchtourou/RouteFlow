import uuid
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from app.core.pagination import PageParams
from app.core.types import SearchTerm
from app.modules.warehouses.models import (
    DockDirection,
    DockStatus,
    EquipmentStatus,
    EquipmentType,
    WarehouseStatus,
)
from app.modules.warehouses.rules import UtilizationLevel


class WarehouseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    name: str
    location: str
    latitude: float
    longitude: float
    capacity: int = Field(description="Pallet positions")
    current_utilization: int = Field(description="Occupied pallet positions")
    utilization_pct: float
    utilization_level: UtilizationLevel
    status: WarehouseStatus
    created_at: datetime
    updated_at: datetime

    @field_serializer("utilization_pct")
    def _round_pct(self, value: float) -> float:
        return round(value, 1)


class WarehouseListItem(WarehouseRead):
    sku_count: int
    low_stock_count: int = Field(description="Items at or below their reorder threshold")


class InventorySummary(BaseModel):
    sku_count: int
    total_quantity: int
    reserved_quantity: int
    available_quantity: int
    low_stock_count: int
    out_of_stock_count: int


class DockSummary(BaseModel):
    total: int
    inbound: int
    outbound: int
    out_of_service: int


class EquipmentSummary(BaseModel):
    total: int
    by_status: dict[EquipmentStatus, int]


class WarehouseDetail(WarehouseRead):
    """Everything an operator (or the AI agent) needs to judge a site at a glance."""

    inventory: InventorySummary
    docks: DockSummary
    equipment: EquipmentSummary


class WarehouseSort(StrEnum):
    CODE = "code"
    NAME = "name"
    UTILIZATION = "utilization"
    UTILIZATION_DESC = "-utilization"
    LOW_STOCK_DESC = "-low_stock"


class WarehouseListParams(PageParams):
    model_config = ConfigDict(extra="forbid")

    status: list[WarehouseStatus] | None = Field(default=None, description="Repeatable")
    utilization_level: list[UtilizationLevel] | None = Field(default=None, description="Repeatable")
    location: SearchTerm | None = Field(default=None, description="City, case-insensitive")
    search: SearchTerm | None = Field(default=None, description="Substring of code or name")
    sort: WarehouseSort = WarehouseSort.CODE


class DockRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    direction: DockDirection
    status: DockStatus
    position: int


class EquipmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    equipment_type: EquipmentType
    status: EquipmentStatus
    battery_level: float
