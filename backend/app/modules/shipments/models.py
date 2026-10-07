from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, enum_checks, enum_column

if TYPE_CHECKING:
    from app.modules.exceptions.models import ShipmentException
    from app.modules.orders.models import Order
    from app.modules.routes.models import Route
    from app.modules.tracking.models import TrackingEvent
    from app.modules.vehicles.models import Vehicle
    from app.modules.warehouses.models import Warehouse


class ShipmentStatus(StrEnum):
    CREATED = "CREATED"
    PICKED = "PICKED"
    PACKED = "PACKED"
    LOADED = "LOADED"
    IN_TRANSIT = "IN_TRANSIT"
    OUT_FOR_DELIVERY = "OUT_FOR_DELIVERY"
    DELIVERED = "DELIVERED"


class TemperatureStatus(StrEnum):
    NOT_APPLICABLE = "NOT_APPLICABLE"  # ambient goods
    NORMAL = "NORMAL"
    DEVIATION = "DEVIATION"


class Shipment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "shipments"
    __table_args__ = (
        *enum_checks(status=ShipmentStatus, temperature_status=TemperatureStatus),
        CheckConstraint(
            "actual_delivery IS NULL OR status = 'DELIVERED'",
            name="actual_delivery_only_when_delivered",
        ),
        Index("ix_shipments_order_id", "order_id"),
        Index("ix_shipments_warehouse_id", "warehouse_id"),
        Index("ix_shipments_route_id", "route_id"),
        Index("ix_shipments_vehicle_id", "vehicle_id"),
        Index("ix_shipments_status", "status"),
        Index("ix_shipments_destination", "destination"),
        Index("ix_shipments_estimated_delivery", "estimated_delivery"),
    )

    shipment_number: Mapped[str] = mapped_column(String(32), unique=True)
    order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("orders.id", ondelete="RESTRICT"))
    warehouse_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("warehouses.id", ondelete="RESTRICT")
    )
    route_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("routes.id", ondelete="SET NULL"))
    vehicle_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("vehicles.id", ondelete="SET NULL")
    )
    status: Mapped[ShipmentStatus] = mapped_column(
        enum_column(ShipmentStatus, "shipment_status"), default=ShipmentStatus.CREATED
    )
    origin: Mapped[str] = mapped_column(String(80))
    destination: Mapped[str] = mapped_column(String(80))
    carrier: Mapped[str] = mapped_column(String(80))
    estimated_delivery: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    actual_delivery: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    temperature_status: Mapped[TemperatureStatus] = mapped_column(
        enum_column(TemperatureStatus, "temperature_status"),
        default=TemperatureStatus.NOT_APPLICABLE,
    )

    order: Mapped[Order] = relationship(back_populates="shipments", lazy="raise")
    warehouse: Mapped[Warehouse] = relationship(back_populates="shipments", lazy="raise")
    route: Mapped[Route | None] = relationship(back_populates="shipments", lazy="raise")
    vehicle: Mapped[Vehicle | None] = relationship(back_populates="shipments", lazy="raise")
    tracking_events: Mapped[list[TrackingEvent]] = relationship(
        back_populates="shipment",
        lazy="raise",
        cascade="all, delete-orphan",
        order_by="TrackingEvent.occurred_at",
    )
    exceptions: Mapped[list[ShipmentException]] = relationship(
        back_populates="shipment", lazy="raise", cascade="all, delete-orphan"
    )
