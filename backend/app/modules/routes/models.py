from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Float, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, enum_checks, enum_column

if TYPE_CHECKING:
    from app.modules.shipments.models import Shipment


class RouteStatus(StrEnum):
    PLANNED = "PLANNED"
    ACTIVE = "ACTIVE"
    DELAYED = "DELAYED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class RiskLevel(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class Route(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "routes"
    __table_args__ = (
        *enum_checks(status=RouteStatus, risk_level=RiskLevel),
        CheckConstraint("distance_km > 0", name="distance_positive"),
        CheckConstraint("estimated_duration_minutes > 0", name="duration_positive"),
        Index("ix_routes_status", "status"),
        Index("ix_routes_risk_level", "risk_level"),
    )

    route_number: Mapped[str] = mapped_column(String(16), unique=True)
    origin: Mapped[str] = mapped_column(String(80))
    destination: Mapped[str] = mapped_column(String(80))
    distance_km: Mapped[float] = mapped_column(Float)
    estimated_duration_minutes: Mapped[int] = mapped_column(Integer)
    status: Mapped[RouteStatus] = mapped_column(
        enum_column(RouteStatus, "route_status"), default=RouteStatus.PLANNED
    )
    risk_level: Mapped[RiskLevel] = mapped_column(
        enum_column(RiskLevel, "risk_level"), default=RiskLevel.LOW
    )

    shipments: Mapped[list[Shipment]] = relationship(back_populates="route", lazy="raise")
