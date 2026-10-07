from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, enum_checks, enum_column
from app.modules.warehouses.models import DockDirection

if TYPE_CHECKING:
    from app.modules.shipments.models import Shipment
    from app.modules.warehouses.models import Dock


class DockAppointment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One truck visit to one dock door. Only the plan is stored; the visit's current state
    (en route, waiting, loading, ...) is derived from these timestamps (see `rules.py`)."""

    __tablename__ = "dock_appointments"
    __table_args__ = (
        *enum_checks(direction=DockDirection),
        UniqueConstraint("dock_id", "sequence", name="uq_dock_appointments_dock_sequence"),
        CheckConstraint(
            "arrives_at < docked_at AND docked_at < departs_at", name="timeline_ordered"
        ),
        CheckConstraint("pallets_total > 0", name="pallets_positive"),
        CheckConstraint("sequence >= 0", name="sequence_non_negative"),
        Index("ix_dock_appointments_warehouse_departs", "warehouse_id", "departs_at"),
        Index("ix_dock_appointments_shipment_id", "shipment_id"),
    )

    warehouse_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("warehouses.id", ondelete="CASCADE"))
    dock_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("docks.id", ondelete="CASCADE"))
    shipment_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("shipments.id", ondelete="SET NULL")
    )
    # Order of visits at this dock; also what makes the simulator's top-up idempotent.
    sequence: Mapped[int] = mapped_column(Integer)
    truck_code: Mapped[str] = mapped_column(String(16))
    carrier: Mapped[str] = mapped_column(String(80))
    direction: Mapped[DockDirection] = mapped_column(enum_column(DockDirection, "dock_direction"))
    arrives_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    docked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    departs_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    pallets_total: Mapped[int] = mapped_column(Integer)

    dock: Mapped[Dock] = relationship(lazy="raise")
    shipment: Mapped[Shipment | None] = relationship(lazy="raise")
