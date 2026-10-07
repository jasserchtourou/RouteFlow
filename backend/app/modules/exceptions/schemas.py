import uuid
from datetime import datetime
from enum import StrEnum
from typing import Annotated, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.pagination import PageParams
from app.core.types import SearchTerm, WarehouseCode, text
from app.modules.exceptions.models import ExceptionSeverity, ExceptionStatus, ExceptionType

Description = Annotated[str, text(1000)]


class ExceptionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    shipment_id: uuid.UUID
    shipment_number: str
    warehouse_code: str
    destination: str
    type: ExceptionType
    severity: ExceptionSeverity
    status: ExceptionStatus
    description: str
    created_at: datetime
    resolved_at: datetime | None
    resolution_note: str | None


class ExceptionCreate(BaseModel):
    """Manually raise an incident on a shipment (e.g. damage found at the dock)."""

    model_config = ConfigDict(extra="forbid")

    type: ExceptionType
    severity: ExceptionSeverity
    description: Description


class ExceptionUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: ExceptionStatus | None = None
    severity: ExceptionSeverity | None = None
    resolution_note: Description | None = None

    @model_validator(mode="after")
    def _validate(self) -> Self:
        nulls = sorted(name for name in self.model_fields_set if getattr(self, name) is None)
        if nulls:
            raise ValueError(f"fields cannot be null: {', '.join(nulls)}")
        if not self.model_fields_set:
            raise ValueError("at least one field must be provided")
        return self


class ExceptionSort(StrEnum):
    SEVERITY_DESC = "-severity"  # most severe first, then newest
    CREATED_AT = "created_at"
    CREATED_AT_DESC = "-created_at"


class ExceptionListParams(PageParams):
    model_config = ConfigDict(extra="forbid")

    active: bool | None = Field(
        default=None, description="true: OPEN + INVESTIGATING; false: RESOLVED"
    )
    status: list[ExceptionStatus] | None = Field(default=None, description="Repeatable")
    type: list[ExceptionType] | None = Field(default=None, description="Repeatable")
    severity: list[ExceptionSeverity] | None = Field(default=None, description="Repeatable")
    warehouse_code: list[WarehouseCode] | None = Field(default=None, description="Repeatable")
    shipment_number: SearchTerm | None = None
    sort: ExceptionSort = ExceptionSort.SEVERITY_DESC
