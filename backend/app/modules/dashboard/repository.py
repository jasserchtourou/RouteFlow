"""Aggregate read queries for the operations dashboard (read model across modules)."""

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import DayWindow
from app.modules.exceptions.models import ExceptionSeverity, ExceptionType, ShipmentException
from app.modules.exceptions.rules import ACTIVE_STATUSES
from app.modules.orders.models import Order, OrderStatus
from app.modules.shipments.models import Shipment, ShipmentStatus


class DashboardRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def orders_by_status(self) -> dict[OrderStatus, int]:
        rows = await self.session.execute(select(Order.status, func.count()).group_by(Order.status))
        return dict.fromkeys(OrderStatus, 0) | dict(rows.all())

    async def orders_created_in(self, window: DayWindow) -> int:
        count = await self.session.scalar(
            select(func.count()).where(
                Order.created_at >= window.start, Order.created_at < window.end
            )
        )
        return count or 0

    async def shipments_by_status(self) -> dict[ShipmentStatus, int]:
        rows = await self.session.execute(
            select(Shipment.status, func.count()).group_by(Shipment.status)
        )
        return dict.fromkeys(ShipmentStatus, 0) | dict(rows.all())

    async def delayed_shipments(self, now: datetime) -> int:
        count = await self.session.scalar(
            select(func.count()).where(
                Shipment.status != ShipmentStatus.DELIVERED, Shipment.estimated_delivery < now
            )
        )
        return count or 0

    async def deliveries(self, start: datetime, end: datetime) -> tuple[int, int]:
        """(delivered, on time) for deliveries in [start, end), measured against the promise
        made to the customer on the order."""
        delivered, on_time = (
            await self.session.execute(
                select(
                    func.count(),
                    func.count().filter(Shipment.actual_delivery <= Order.promised_delivery_at),
                )
                .select_from(Shipment)
                .join(Order, Order.id == Shipment.order_id)
                .where(
                    Shipment.status == ShipmentStatus.DELIVERED,
                    Shipment.actual_delivery >= start,
                    Shipment.actual_delivery < end,
                )
            )
        ).one()
        return delivered, on_time

    async def active_exceptions_by_severity(self) -> dict[ExceptionSeverity, int]:
        rows = await self.session.execute(
            select(ShipmentException.severity, func.count())
            .where(ShipmentException.status.in_(ACTIVE_STATUSES))
            .group_by(ShipmentException.severity)
        )
        return dict.fromkeys(ExceptionSeverity, 0) | dict(rows.all())

    async def active_exceptions_by_type(self) -> dict[ExceptionType, int]:
        rows = await self.session.execute(
            select(ShipmentException.type, func.count())
            .where(ShipmentException.status.in_(ACTIVE_STATUSES))
            .group_by(ShipmentException.type)
        )
        return dict.fromkeys(ExceptionType, 0) | dict(rows.all())
