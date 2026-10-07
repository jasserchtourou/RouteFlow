import uuid
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from app.core.pagination import PageParams
from app.core.types import Place, SearchTerm
from app.modules.routes.models import RiskLevel, RouteStatus
from app.modules.shipments.schemas import ShipmentRead


class RiskAssessmentRead(BaseModel):
    score: int = Field(ge=0, le=100)
    level: RiskLevel
    factors: list[str] = Field(description="Why the route scores this way")


class RouteRead(BaseModel):
    id: uuid.UUID
    route_number: str
    origin: str
    destination: str
    distance_km: float
    estimated_duration_minutes: int
    status: RouteStatus
    planned_risk_level: RiskLevel
    active_shipments: int
    delayed_shipments: int
    max_delay_minutes: int
    serious_exceptions: int = Field(description="Active HIGH/CRITICAL exceptions")
    risk: RiskAssessmentRead


class RouteDetail(RouteRead):
    shipments: list[ShipmentRead] = Field(description="Active shipments, most overdue first")


class RouteSort(StrEnum):
    ROUTE_NUMBER = "route_number"
    DISTANCE = "distance"
    DISTANCE_DESC = "-distance"
    PLANNED_RISK_DESC = "-planned_risk"


class RouteListParams(PageParams):
    model_config = ConfigDict(extra="forbid")

    status: list[RouteStatus] | None = Field(default=None, description="Repeatable")
    planned_risk_level: list[RiskLevel] | None = Field(default=None, description="Repeatable")
    origin: Place | None = None
    destination: Place | None = None
    delayed: bool | None = Field(
        default=None, description="true: flagged DELAYED or carrying delayed shipments"
    )
    search: SearchTerm | None = Field(default=None, description="Route number or city")
    sort: RouteSort = RouteSort.ROUTE_NUMBER


class AtRiskParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    limit: int = Field(default=10, ge=1, le=50)
    min_level: RiskLevel = Field(default=RiskLevel.MEDIUM, description="Lowest level to include")
