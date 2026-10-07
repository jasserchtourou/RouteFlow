from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Index, Sequence, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, enum_checks, enum_column

if TYPE_CHECKING:
    from app.modules.shipments.models import Shipment


# Source of server-generated order numbers (ORD-20001, ...). Seeded orders use 10001-19999.
ORDER_NUMBER_SEQUENCE = Sequence("order_number_seq", start=20001, metadata=Base.metadata)
ORDER_NUMBER_PREFIX = "ORD-"


class OrderStatus(StrEnum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    PROCESSING = "PROCESSING"
    SHIPPED = "SHIPPED"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"


class OrderPriority(StrEnum):
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    URGENT = "URGENT"


class Order(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "orders"
    __table_args__ = (
        *enum_checks(status=OrderStatus, priority=OrderPriority),
        Index("ix_orders_status", "status"),
        Index("ix_orders_destination", "destination"),
        Index("ix_orders_created_at", "created_at"),
        Index("ix_orders_promised_delivery_at", "promised_delivery_at"),
    )

    order_number: Mapped[str] = mapped_column(String(32), unique=True)
    customer_name: Mapped[str] = mapped_column(String(120))
    origin: Mapped[str] = mapped_column(String(80))
    destination: Mapped[str] = mapped_column(String(80))
    status: Mapped[OrderStatus] = mapped_column(
        enum_column(OrderStatus, "order_status"), default=OrderStatus.PENDING
    )
    priority: Mapped[OrderPriority] = mapped_column(
        enum_column(OrderPriority, "order_priority"), default=OrderPriority.NORMAL
    )
    promised_delivery_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    shipments: Mapped[list[Shipment]] = relationship(back_populates="order", lazy="raise")
