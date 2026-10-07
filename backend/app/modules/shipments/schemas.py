import uuid
from datetime import datetime
from enum import StrEnum
from typing import Self

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from app.core.pagination import PageParams
from app.core.types import Place, SearchTerm, WarehouseCode
from app.modules.exceptions.schemas import ExceptionRead
from app.modules.shipments.models import ShipmentStatus, TemperatureStatus
from app.modules.tracking.schemas import TrackingEventRead


class ShipmentRead(BaseModel):
    id: uuid.UUID
    shipment_number: str
    status: ShipmentStatus
    order_id: uuid.UUID
    order_number: str
    warehouse_id: uuid.UUID
    warehouse_code: str
    route_id: uuid.UUID | None
    route_number: str | None
    vehicle_id: uuid.UUID | None
    vehicle_registration: str | None
    origin: str
    destination: str
    carrier: str
    estimated_delivery: datetime
    actual_delivery: datetime | None
    temperature_status: TemperatureStatus
    is_delayed: bool = Field(description="Not delivered and the ETA has passed")
    delay_minutes: int = Field(description="Minutes past ETA (final value once delivered)")
    active_exception_count: int
    created_at: datetime
    updated_at: datetime


class ShipmentDetail(ShipmentRead):
    latest_event: TrackingEventRead | None
    active_exceptions: list[ExceptionRead]


class ShipmentSort(StrEnum):
    ESTIMATED_DELIVERY = "estimated_delivery"  # most overdue / soonest due first
    ESTIMATED_DELIVERY_DESC = "-estimated_delivery"
    CREATED_AT = "created_at"
    CREATED_AT_DESC = "-created_at"
    SHIPMENT_NUMBER = "shipment_number"


class ShipmentListParams(PageParams):
    model_config = ConfigDict(extra="forbid")

    status: list[ShipmentStatus] | None = Field(default=None, description="Repeatable")
    warehouse_code: list[WarehouseCode] | None = Field(default=None, description="Repeatable")
    route_number: SearchTerm | None = Field(default=None, description="e.g. RTE-110")
    vehicle_registration: SearchTerm | None = None
    temperature_status: list[TemperatureStatus] | None = Field(default=None)
    destination: Place | None = Field(default=None, description="City, case-insensitive")
    delayed: bool | None = Field(default=None, description="Only (non-)delayed shipments")
    has_active_exception: bool | None = None
    search: SearchTerm | None = Field(default=None, description="Shipment or order number")
    eta_after: AwareDatetime | None = None
    eta_before: AwareDatetime | None = None
    sort: ShipmentSort = ShipmentSort.CREATED_AT_DESC

    @model_validator(mode="after")
    def _validate_range(self) -> Self:
        if self.eta_after and self.eta_before and self.eta_after > self.eta_before:
            raise ValueError("eta_after must not be later than eta_before")
        return self
