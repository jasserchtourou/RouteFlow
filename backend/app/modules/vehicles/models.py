from __future__ import annotations

import uuid
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Float, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, enum_checks, enum_column

if TYPE_CHECKING:
    from app.modules.drivers.models import Driver
    from app.modules.shipments.models import Shipment


class VehicleType(StrEnum):
    VAN = "VAN"
    TRUCK = "TRUCK"
    REFRIGERATED_TRUCK = "REFRIGERATED_TRUCK"
    SEMI_TRAILER = "SEMI_TRAILER"


class VehicleStatus(StrEnum):
    AVAILABLE = "AVAILABLE"
    IN_TRANSIT = "IN_TRANSIT"
    MAINTENANCE = "MAINTENANCE"
    OFFLINE = "OFFLINE"


class Vehicle(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "vehicles"
    __table_args__ = (
        *enum_checks(vehicle_type=VehicleType, status=VehicleStatus),
        CheckConstraint("fuel_level >= 0 AND fuel_level <= 100", name="fuel_level_percent"),
        CheckConstraint(
            "current_latitude IS NULL OR (current_latitude BETWEEN -90 AND 90)",
            name="latitude_range",
        ),
        CheckConstraint(
            "current_longitude IS NULL OR (current_longitude BETWEEN -180 AND 180)",
            name="longitude_range",
        ),
        Index("ix_vehicles_status", "status"),
    )

    registration: Mapped[str] = mapped_column(String(24), unique=True)
    vehicle_type: Mapped[VehicleType] = mapped_column(enum_column(VehicleType, "vehicle_type"))
    status: Mapped[VehicleStatus] = mapped_column(
        enum_column(VehicleStatus, "vehicle_status"), default=VehicleStatus.AVAILABLE
    )
    current_latitude: Mapped[float | None] = mapped_column(Float)
    current_longitude: Mapped[float | None] = mapped_column(Float)
    fuel_level: Mapped[float] = mapped_column(Float, default=100.0)  # percent
    # unique => a driver is assigned to at most one vehicle (1:1)
    driver_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("drivers.id", ondelete="SET NULL"), unique=True
    )

    driver: Mapped[Driver | None] = relationship(back_populates="vehicle", lazy="raise")
    shipments: Mapped[list[Shipment]] = relationship(back_populates="vehicle", lazy="raise")
