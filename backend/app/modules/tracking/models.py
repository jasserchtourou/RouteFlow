from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base import Base, UUIDPrimaryKeyMixin, enum_checks, enum_column

if TYPE_CHECKING:
    from app.modules.shipments.models import Shipment


class TrackingEventType(StrEnum):
    CREATED = "CREATED"
    PICKED = "PICKED"
    PACKED = "PACKED"
    LOADED = "LOADED"
    DEPARTED = "DEPARTED"
    CHECKPOINT = "CHECKPOINT"
    ARRIVED_HUB = "ARRIVED_HUB"
    OUT_FOR_DELIVERY = "OUT_FOR_DELIVERY"
    DELIVERED = "DELIVERED"
    DELAY_REPORTED = "DELAY_REPORTED"
    TEMPERATURE_ALERT = "TEMPERATURE_ALERT"


class TrackingEvent(UUIDPrimaryKeyMixin, Base):
    """Append-only history, so there is no updated_at."""

    __tablename__ = "tracking_events"
    __table_args__ = (
        *enum_checks(event_type=TrackingEventType),
        # Serves "history of one shipment, in order" and "latest event of a shipment".
        Index("ix_tracking_events_shipment_id_occurred_at", "shipment_id", "occurred_at"),
        Index("ix_tracking_events_occurred_at", "occurred_at"),
    )

    shipment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("shipments.id", ondelete="CASCADE"))
    event_type: Mapped[TrackingEventType] = mapped_column(
        enum_column(TrackingEventType, "tracking_event_type")
    )
    location: Mapped[str] = mapped_column(String(120))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    # Free-form payload (temperature reading, delay minutes, ...). Not called "metadata":
    # that name is reserved by SQLAlchemy's declarative API.
    details: Mapped[dict[str, Any]] = mapped_column(
        JSONB, server_default="{}", default=dict, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    shipment: Mapped[Shipment] = relationship(back_populates="tracking_events", lazy="raise")
