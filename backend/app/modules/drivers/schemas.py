import uuid

from pydantic import BaseModel, ConfigDict, Field

from app.core.pagination import PageParams
from app.core.types import SearchTerm
from app.modules.drivers.models import DriverStatus


class DriverRead(BaseModel):
    id: uuid.UUID
    full_name: str
    license_number: str
    phone: str | None
    status: DriverStatus
    vehicle_id: uuid.UUID | None
    vehicle_registration: str | None


class DriverListParams(PageParams):
    model_config = ConfigDict(extra="forbid")

    status: list[DriverStatus] | None = Field(default=None, description="Repeatable")
    search: SearchTerm | None = Field(default=None, description="Name or license number")
