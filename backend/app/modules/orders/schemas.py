import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated, Self

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from app.core.pagination import PageParams
from app.core.types import SearchTerm, text
from app.modules.orders.models import OrderPriority, OrderStatus

CustomerName = Annotated[str, text(120)]
Place = Annotated[str, text(80)]


def _ensure_future(value: datetime) -> datetime:
    if value <= datetime.now(UTC):
        raise ValueError("promised_delivery_at must be in the future")
    return value


def _ensure_different_places(origin: str | None, destination: str | None) -> None:
    if origin and destination and origin.casefold() == destination.casefold():
        raise ValueError("origin and destination must differ")


class OrderCreate(BaseModel):
    # extra="forbid": unknown fields (typos, or attempts to set status/order_number) are
    # rejected with 422 instead of being silently ignored.
    model_config = ConfigDict(extra="forbid")

    customer_name: CustomerName
    origin: Place
    destination: Place
    priority: OrderPriority = OrderPriority.NORMAL
    promised_delivery_at: AwareDatetime  # timezone required: "2026-10-08T14:00:00Z"

    @model_validator(mode="after")
    def _validate(self) -> Self:
        _ensure_future(self.promised_delivery_at)
        _ensure_different_places(self.origin, self.destination)
        return self


class OrderUpdate(BaseModel):
    """Partial update: only fields present in the request body are changed."""

    model_config = ConfigDict(extra="forbid")

    customer_name: CustomerName | None = None
    origin: Place | None = None
    destination: Place | None = None
    priority: OrderPriority | None = None
    status: OrderStatus | None = None
    promised_delivery_at: AwareDatetime | None = None

    @model_validator(mode="after")
    def _validate(self) -> Self:
        # "Absent" means "leave unchanged"; an explicit null would mean "erase", which no
        # order field allows.
        nulls = sorted(name for name in self.model_fields_set if getattr(self, name) is None)
        if nulls:
            raise ValueError(f"fields cannot be null: {', '.join(nulls)}")
        if not self.model_fields_set:
            raise ValueError("at least one field must be provided")
        if self.promised_delivery_at is not None:
            _ensure_future(self.promised_delivery_at)
        _ensure_different_places(self.origin, self.destination)
        return self

    def changes(self) -> dict[str, object]:
        return self.model_dump(exclude_unset=True)


class OrderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    order_number: str
    customer_name: str
    origin: str
    destination: str
    status: OrderStatus
    priority: OrderPriority
    promised_delivery_at: datetime
    created_at: datetime
    updated_at: datetime


class OrderSort(StrEnum):
    """Whitelisted sort keys; a leading "-" means descending."""

    CREATED_AT = "created_at"
    CREATED_AT_DESC = "-created_at"
    PROMISED_DELIVERY_AT = "promised_delivery_at"
    PROMISED_DELIVERY_AT_DESC = "-promised_delivery_at"
    PRIORITY = "priority"
    PRIORITY_DESC = "-priority"
    ORDER_NUMBER = "order_number"
    ORDER_NUMBER_DESC = "-order_number"
    CUSTOMER_NAME = "customer_name"
    CUSTOMER_NAME_DESC = "-customer_name"


class OrderListParams(PageParams):
    """Query parameters for GET /orders. Unknown parameters are rejected."""

    model_config = ConfigDict(extra="forbid")

    status: list[OrderStatus] | None = Field(default=None, description="Repeatable")
    priority: list[OrderPriority] | None = Field(default=None, description="Repeatable")
    destination: Place | None = Field(default=None, description="Exact city, case-insensitive")
    search: SearchTerm | None = Field(
        default=None, description="Substring of order number or customer name"
    )
    created_after: AwareDatetime | None = None
    created_before: AwareDatetime | None = None
    sort: OrderSort = OrderSort.CREATED_AT_DESC

    @model_validator(mode="after")
    def _validate_range(self) -> Self:
        if self.created_after and self.created_before and self.created_after > self.created_before:
            raise ValueError("created_after must not be later than created_before")
        return self
