from __future__ import annotations

import uuid
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    ColumnElement,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    case,
    cast,
)
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, enum_checks, enum_column
from app.modules.warehouses import rules
from app.modules.warehouses.rules import UtilizationLevel

if TYPE_CHECKING:
    from app.modules.inventory.models import InventoryItem
    from app.modules.shipments.models import Shipment


class WarehouseStatus(StrEnum):
    OPERATIONAL = "OPERATIONAL"
    CONGESTED = "CONGESTED"
    DISRUPTED = "DISRUPTED"
    OFFLINE = "OFFLINE"


class DockDirection(StrEnum):
    INBOUND = "INBOUND"
    OUTBOUND = "OUTBOUND"


class DockStatus(StrEnum):
    """Physical availability. Whether a dock is *occupied* follows from truck appointments
    (Phase 6), so it is derived, not stored here."""

    AVAILABLE = "AVAILABLE"
    OUT_OF_SERVICE = "OUT_OF_SERVICE"


class EquipmentType(StrEnum):
    FORKLIFT = "FORKLIFT"
    REACH_TRUCK = "REACH_TRUCK"
    PALLET_JACK = "PALLET_JACK"


class EquipmentStatus(StrEnum):
    ACTIVE = "ACTIVE"
    IDLE = "IDLE"
    CHARGING = "CHARGING"
    MAINTENANCE = "MAINTENANCE"


class Warehouse(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "warehouses"
    __table_args__ = (
        *enum_checks(status=WarehouseStatus),
        CheckConstraint("capacity > 0", name="capacity_positive"),
        CheckConstraint(
            "current_utilization >= 0 AND current_utilization <= capacity",
            name="utilization_within_capacity",
        ),
        Index("ix_warehouses_status", "status"),
        Index("ix_warehouses_location", "location"),
    )

    code: Mapped[str] = mapped_column(String(16), unique=True)
    name: Mapped[str] = mapped_column(String(120))
    location: Mapped[str] = mapped_column(String(80))  # city
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    capacity: Mapped[int] = mapped_column(Integer)  # in pallet positions
    current_utilization: Mapped[int] = mapped_column(Integer)  # occupied pallet positions
    status: Mapped[WarehouseStatus] = mapped_column(
        enum_column(WarehouseStatus, "warehouse_status"), default=WarehouseStatus.OPERATIONAL
    )

    inventory_items: Mapped[list[InventoryItem]] = relationship(
        back_populates="warehouse", lazy="raise", cascade="all, delete-orphan"
    )
    shipments: Mapped[list[Shipment]] = relationship(back_populates="warehouse", lazy="raise")
    docks: Mapped[list[Dock]] = relationship(
        back_populates="warehouse", lazy="raise", cascade="all, delete-orphan"
    )
    equipment: Mapped[list[Equipment]] = relationship(
        back_populates="warehouse", lazy="raise", cascade="all, delete-orphan"
    )

    @hybrid_property
    def utilization_pct(self) -> float:
        return rules.utilization_pct(self.current_utilization, self.capacity)

    @utilization_pct.inplace.expression
    @classmethod
    def _utilization_pct_expression(cls) -> ColumnElement[float]:
        # Cast to double precision: `100.0` alone is NUMERIC in PostgreSQL (-> Decimal).
        return cast(cls.current_utilization * 100.0 / cls.capacity, Float)

    @hybrid_property
    def utilization_level(self) -> UtilizationLevel:
        return rules.utilization_level(self.utilization_pct)

    @utilization_level.inplace.expression
    @classmethod
    def _utilization_level_expression(cls) -> ColumnElement[str]:
        pct = cast(cls.current_utilization * 100.0 / cls.capacity, Float)
        return case(
            (pct >= rules.CRITICAL_UTILIZATION_PCT, UtilizationLevel.CRITICAL.value),
            (pct >= rules.HIGH_UTILIZATION_PCT, UtilizationLevel.HIGH.value),
            else_=UtilizationLevel.NORMAL.value,
        )


class Dock(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A dock door (e.g. "In 2"). `position` is its slot along the building facade, which the
    3D view uses for layout."""

    __tablename__ = "docks"
    __table_args__ = (
        *enum_checks(direction=DockDirection, status=DockStatus),
        UniqueConstraint("warehouse_id", "code", name="uq_docks_warehouse_code"),
        UniqueConstraint("warehouse_id", "position", name="uq_docks_warehouse_position"),
        CheckConstraint("position >= 1", name="position_positive"),
    )

    warehouse_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("warehouses.id", ondelete="CASCADE"))
    code: Mapped[str] = mapped_column(String(16))
    direction: Mapped[DockDirection] = mapped_column(enum_column(DockDirection, "dock_direction"))
    status: Mapped[DockStatus] = mapped_column(
        enum_column(DockStatus, "dock_status"), default=DockStatus.AVAILABLE
    )
    position: Mapped[int] = mapped_column(Integer)

    warehouse: Mapped[Warehouse] = relationship(back_populates="docks", lazy="raise")


class Equipment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Material-handling equipment on site (forklifts, reach trucks, pallet jacks)."""

    __tablename__ = "equipment"
    __table_args__ = (
        *enum_checks(equipment_type=EquipmentType, status=EquipmentStatus),
        UniqueConstraint("warehouse_id", "code", name="uq_equipment_warehouse_code"),
        CheckConstraint(
            "battery_level >= 0 AND battery_level <= 100", name="battery_level_percent"
        ),
    )

    warehouse_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("warehouses.id", ondelete="CASCADE"))
    code: Mapped[str] = mapped_column(String(16))
    equipment_type: Mapped[EquipmentType] = mapped_column(
        enum_column(EquipmentType, "equipment_type")
    )
    status: Mapped[EquipmentStatus] = mapped_column(
        enum_column(EquipmentStatus, "equipment_status"), default=EquipmentStatus.IDLE
    )
    battery_level: Mapped[float] = mapped_column(Float, default=100.0)

    warehouse: Mapped[Warehouse] = relationship(back_populates="equipment", lazy="raise")
