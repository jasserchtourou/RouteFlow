"""Data access for shipment exceptions."""

import uuid
from collections.abc import Sequence

from sqlalchemy import Row, Select, case, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.querying import paginate_rows
from app.modules.exceptions.models import ExceptionType, ShipmentException
from app.modules.exceptions.rules import ACTIVE_STATUSES, SEVERITY_RANK
from app.modules.exceptions.schemas import ExceptionListParams, ExceptionSort
from app.modules.shipments.models import Shipment
from app.modules.warehouses.models import Warehouse

ExceptionRow = Row[ShipmentException, str, str, str]
ExceptionQuery = Select[ShipmentException, str, str, str]

_SEVERITY_RANK = case(
    {severity.value: rank for severity, rank in SEVERITY_RANK.items()},
    value=ShipmentException.severity,
)


def _with_context() -> ExceptionQuery:
    """Exceptions plus the shipment/warehouse context an operator needs to act on them."""
    return (
        select(ShipmentException, Shipment.shipment_number, Warehouse.code, Shipment.destination)
        .join(Shipment, Shipment.id == ShipmentException.shipment_id)
        .join(Warehouse, Warehouse.id == Shipment.warehouse_id)
    )


class ExceptionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, exception_id: uuid.UUID) -> ShipmentException | None:
        return await self.session.get(ShipmentException, exception_id)

    async def get_row(self, exception_id: uuid.UUID) -> ExceptionRow | None:
        result = await self.session.execute(
            _with_context().where(ShipmentException.id == exception_id)
        )
        return result.one_or_none()

    async def find_active(
        self, shipment_id: uuid.UUID, kind: ExceptionType
    ) -> ShipmentException | None:
        return await self.session.scalar(
            select(ShipmentException).where(
                ShipmentException.shipment_id == shipment_id,
                ShipmentException.type == kind,
                ShipmentException.status.in_(ACTIVE_STATUSES),
            )
        )

    async def active_for_shipment(self, shipment_id: uuid.UUID) -> Sequence[ExceptionRow]:
        result = await self.session.execute(
            _with_context()
            .where(
                ShipmentException.shipment_id == shipment_id,
                ShipmentException.status.in_(ACTIVE_STATUSES),
            )
            .order_by(_SEVERITY_RANK.desc(), ShipmentException.created_at.desc())
        )
        return result.all()

    async def rows_by_ids(self, ids: Sequence[uuid.UUID]) -> Sequence[ExceptionRow]:
        if not ids:
            return []
        result = await self.session.execute(
            _with_context().where(ShipmentException.id.in_(ids)).order_by(_SEVERITY_RANK.desc())
        )
        return result.all()

    async def list(self, params: ExceptionListParams) -> tuple[Sequence[ExceptionRow], int]:
        query = _with_context()
        if params.active is True:
            query = query.where(ShipmentException.status.in_(ACTIVE_STATUSES))
        elif params.active is False:
            query = query.where(ShipmentException.status.not_in(ACTIVE_STATUSES))
        if params.status:
            query = query.where(ShipmentException.status.in_(params.status))
        if params.type:
            query = query.where(ShipmentException.type.in_(params.type))
        if params.severity:
            query = query.where(ShipmentException.severity.in_(params.severity))
        if params.warehouse_code:
            query = query.where(Warehouse.code.in_(params.warehouse_code))
        if params.shipment_number:
            query = query.where(Shipment.shipment_number == params.shipment_number.upper())
        return await paginate_rows(self.session, _sorted(query, params.sort), params)

    def add(self, exception: ShipmentException) -> None:
        self.session.add(exception)


def _sorted(query: ExceptionQuery, sort: ExceptionSort) -> ExceptionQuery:
    newest = ShipmentException.created_at.desc()
    if sort == ExceptionSort.SEVERITY_DESC:
        return query.order_by(_SEVERITY_RANK.desc(), newest, ShipmentException.id)
    if sort == ExceptionSort.CREATED_AT:
        return query.order_by(ShipmentException.created_at.asc(), ShipmentException.id)
    return query.order_by(newest, ShipmentException.id)
