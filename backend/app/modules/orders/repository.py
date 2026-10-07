"""Data access for orders: query construction only, no business rules, never commits."""

import uuid
from collections.abc import Sequence

from sqlalchemy import Select, case, exists, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.querying import Column, apply_sort, contains_any, paginate
from app.modules.orders.models import (
    ORDER_NUMBER_PREFIX,
    ORDER_NUMBER_SEQUENCE,
    Order,
    OrderPriority,
)
from app.modules.orders.schemas import OrderListParams
from app.modules.shipments.models import Shipment, ShipmentStatus

OrderQuery = Select[Order]

# Business order (LOW < NORMAL < HIGH < URGENT), not alphabetical order of the stored strings.
_PRIORITY_RANK = case({p.value: rank for rank, p in enumerate(OrderPriority)}, value=Order.priority)
_SORT_COLUMNS: dict[str, Column] = {
    "created_at": Order.created_at,
    "promised_delivery_at": Order.promised_delivery_at,
    "priority": _PRIORITY_RANK,
    "order_number": Order.order_number,
    "customer_name": Order.customer_name,
}


class OrderRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, order_id: uuid.UUID) -> Order | None:
        return await self.session.get(Order, order_id)

    async def get_by_number(self, order_number: str) -> Order | None:
        return await self.session.scalar(select(Order).where(Order.order_number == order_number))

    async def list(self, params: OrderListParams) -> tuple[Sequence[Order], int]:
        query = self._apply_filters(select(Order), params)
        query = apply_sort(query, params.sort.value, _SORT_COLUMNS, tiebreaker=Order.id)
        return await paginate(self.session, query, params)

    async def next_order_number(self) -> str:
        number = await self.session.scalar(select(ORDER_NUMBER_SEQUENCE.next_value()))
        return f"{ORDER_NUMBER_PREFIX}{number}"

    async def has_shipments(self, order_id: uuid.UUID) -> bool:
        return bool(
            await self.session.scalar(select(exists().where(Shipment.order_id == order_id)))
        )

    async def has_undelivered_shipments(self, order_id: uuid.UUID) -> bool:
        return bool(
            await self.session.scalar(
                select(
                    exists().where(
                        Shipment.order_id == order_id,
                        Shipment.status != ShipmentStatus.DELIVERED,
                    )
                )
            )
        )

    def add(self, order: Order) -> None:
        self.session.add(order)

    async def delete(self, order: Order) -> None:
        await self.session.delete(order)

    @staticmethod
    def _apply_filters(query: OrderQuery, params: OrderListParams) -> OrderQuery:
        if params.status:
            query = query.where(Order.status.in_(params.status))
        if params.priority:
            query = query.where(Order.priority.in_(params.priority))
        if params.destination:
            query = query.where(func.lower(Order.destination) == params.destination.lower())
        if params.search:
            query = query.where(
                contains_any(params.search, Order.order_number, Order.customer_name)
            )
        if params.created_after:
            query = query.where(Order.created_at >= params.created_after)
        if params.created_before:
            query = query.where(Order.created_at <= params.created_before)
        return query
