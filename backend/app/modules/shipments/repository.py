"""Data access for shipments."""

import uuid
from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import Row, Select, func, not_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.querying import Column, apply_sort, contains_any, paginate_rows
from app.modules.exceptions.models import ShipmentException
from app.modules.exceptions.rules import ACTIVE_STATUSES
from app.modules.orders.models import Order
from app.modules.routes.models import Route
from app.modules.shipments.models import Shipment, ShipmentStatus
from app.modules.shipments.schemas import ShipmentListParams
from app.modules.vehicles.models import Vehicle
from app.modules.warehouses.models import Warehouse

ShipmentRow = Row[Shipment, str, str, str | None, str | None, int]
ShipmentQuery = Select[Shipment, str, str, str | None, str | None, int]

_active_exceptions = (
    select(ShipmentException.shipment_id, func.count().label("active"))
    .where(ShipmentException.status.in_(ACTIVE_STATUSES))
    .group_by(ShipmentException.shipment_id)
    .subquery()
)
_ACTIVE_COUNT = func.coalesce(_active_exceptions.c.active, 0)

_SORT_COLUMNS: dict[str, Column] = {
    "estimated_delivery": Shipment.estimated_delivery,
    "created_at": Shipment.created_at,
    "shipment_number": Shipment.shipment_number,
}


def _with_context() -> ShipmentQuery:
    """Shipments plus the human-readable references of everything they point to (one query)."""
    query: ShipmentQuery = (
        select(
            Shipment,
            Order.order_number,
            Warehouse.code,
            Route.route_number,
            Vehicle.registration,
            _ACTIVE_COUNT,
        )
        .join(Order, Order.id == Shipment.order_id)
        .join(Warehouse, Warehouse.id == Shipment.warehouse_id)
        .outerjoin(Route, Route.id == Shipment.route_id)
        .outerjoin(Vehicle, Vehicle.id == Shipment.vehicle_id)
        .outerjoin(_active_exceptions, _active_exceptions.c.shipment_id == Shipment.id)
    )
    return query


class ShipmentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, shipment_id: uuid.UUID) -> Shipment | None:
        return await self.session.get(Shipment, shipment_id)

    async def get_for_update(self, shipment_id: uuid.UUID) -> Shipment | None:
        """Load and row-lock (SELECT ... FOR UPDATE) until the transaction ends.

        Two events for the same shipment arriving at once are then applied one after the
        other, so both cannot pass the "is this the next status?" check from the same state.
        """
        return await self.session.scalar(
            select(Shipment)
            .where(Shipment.id == shipment_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )

    async def get_row(self, shipment_id: uuid.UUID) -> ShipmentRow | None:
        result = await self.session.execute(_with_context().where(Shipment.id == shipment_id))
        return result.one_or_none()

    async def get_row_by_number(self, shipment_number: str) -> ShipmentRow | None:
        result = await self.session.execute(
            _with_context().where(Shipment.shipment_number == shipment_number.upper())
        )
        return result.one_or_none()

    async def list(
        self, params: ShipmentListParams, now: datetime
    ) -> tuple[Sequence[ShipmentRow], int]:
        query = _with_context()
        if params.status:
            query = query.where(Shipment.status.in_(params.status))
        if params.warehouse_code:
            query = query.where(Warehouse.code.in_(params.warehouse_code))
        if params.route_number:
            query = query.where(Route.route_number == params.route_number.upper())
        if params.vehicle_registration:
            query = query.where(Vehicle.registration == params.vehicle_registration.upper())
        if params.temperature_status:
            query = query.where(Shipment.temperature_status.in_(params.temperature_status))
        if params.destination:
            query = query.where(func.lower(Shipment.destination) == params.destination.lower())
        if params.delayed is not None:
            delayed = (Shipment.status != ShipmentStatus.DELIVERED) & (
                Shipment.estimated_delivery < now
            )
            query = query.where(delayed if params.delayed else not_(delayed))
        if params.has_active_exception is not None:
            query = query.where(
                _ACTIVE_COUNT > 0 if params.has_active_exception else _ACTIVE_COUNT == 0
            )
        if params.search:
            query = query.where(
                contains_any(params.search, Shipment.shipment_number, Order.order_number)
            )
        if params.eta_after:
            query = query.where(Shipment.estimated_delivery >= params.eta_after)
        if params.eta_before:
            query = query.where(Shipment.estimated_delivery <= params.eta_before)
        query = apply_sort(query, params.sort.value, _SORT_COLUMNS, tiebreaker=Shipment.id)
        return await paginate_rows(self.session, query, params)
