from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base import Base, UUIDPrimaryKeyMixin, enum_checks, enum_column

if TYPE_CHECKING:
    from app.modules.shipments.models import Shipment


class ExceptionType(StrEnum):
    DELAYED = "DELAYED"
    TEMPERATURE_DEVIATION = "TEMPERATURE_DEVIATION"
    DAMAGED = "DAMAGED"
    MISSING_DOCUMENT = "MISSING_DOCUMENT"
    STOCK_SHORTAGE = "STOCK_SHORTAGE"


class ExceptionSeverity(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ExceptionStatus(StrEnum):
    OPEN = "OPEN"
    INVESTIGATING = "INVESTIGATING"
    RESOLVED = "RESOLVED"


class ShipmentException(UUIDPrimaryKeyMixin, Base):
    """An operational problem on a shipment.

    Named ShipmentException (table `shipment_exceptions`) to avoid shadowing Python's
    built-in Exception.
    """

    __tablename__ = "shipment_exceptions"
    __table_args__ = (
        *enum_checks(type=ExceptionType, severity=ExceptionSeverity, status=ExceptionStatus),
        CheckConstraint(
            "(status = 'RESOLVED') = (resolved_at IS NOT NULL)",
            name="resolved_at_matches_status",
        ),
        CheckConstraint(
            "status <> 'RESOLVED' OR resolution_note IS NOT NULL",
            name="resolution_note_when_resolved",
        ),
        Index("ix_shipment_exceptions_shipment_id", "shipment_id"),
        Index("ix_shipment_exceptions_status_severity", "status", "severity"),
        # Partial unique index: at most one *active* incident per type and shipment, while any
        # number of resolved ones may exist as history.
        Index(
            "uq_shipment_exceptions_active_type",
            "shipment_id",
            "type",
            unique=True,
            postgresql_where=text("status <> 'RESOLVED'"),
        ),
    )

    shipment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("shipments.id", ondelete="CASCADE"))
    type: Mapped[ExceptionType] = mapped_column(enum_column(ExceptionType, "exception_type"))
    severity: Mapped[ExceptionSeverity] = mapped_column(
        enum_column(ExceptionSeverity, "exception_severity")
    )
    description: Mapped[str] = mapped_column(Text)
    status: Mapped[ExceptionStatus] = mapped_column(
        enum_column(ExceptionStatus, "exception_status"), default=ExceptionStatus.OPEN
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolution_note: Mapped[str | None] = mapped_column(Text)

    shipment: Mapped[Shipment] = relationship(back_populates="exceptions", lazy="raise")
