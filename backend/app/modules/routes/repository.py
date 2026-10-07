"""Data access for routes, with live shipment statistics aggregated per route."""

import uuid
from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import (
    DateTime,
    Integer,
    Row,
    Select,
    case,
    cast,
    exists,
    func,
    literal,
    not_,
    or_,
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.querying import Column, apply_sort, contains_any, paginate_rows
from app.modules.exceptions.models import ExceptionSeverity, ShipmentException
from app.modules.exceptions.rules import ACTIVE_STATUSES
from app.modules.routes.models import RiskLevel, Route, RouteStatus
from app.modules.routes.schemas import RouteListParams
from app.modules.shipments.models import Shipment, ShipmentStatus

# Route, active, delayed, max_delay_minutes, serious_exceptions
RouteRow = Row[Route, int, int, int, int]
RouteQuery = Select[Route, int, int, int, int]

_PLANNED_RISK_RANK = case(
    {level.value: rank for rank, level in enumerate(RiskLevel)}, value=Route.risk_level
)
SERIOUS = (ExceptionSeverity.HIGH, ExceptionSeverity.CRITICAL)


def _with_stats(now: datetime) -> RouteQuery:
    """Routes plus live statistics in one query (two grouped subqueries, no N+1)."""
    open_shipment = Shipment.status != ShipmentStatus.DELIVERED
    delayed = open_shipment & (Shipment.estimated_delivery < now)
    overdue_minutes = (
        func.extract("epoch", literal(now, DateTime(timezone=True)) - Shipment.estimated_delivery)
        / 60
    )
    shipment_stats = (
        select(
            Shipment.route_id,
            func.count().filter(open_shipment).label("active"),
            func.count().filter(delayed).label("delayed"),
            cast(func.floor(func.max(overdue_minutes).filter(delayed)), Integer).label("max_delay"),
        )
        .where(Shipment.route_id.is_not(None))
        .group_by(Shipment.route_id)
        .subquery()
    )
    exception_stats = (
        select(Shipment.route_id, func.count().label("serious"))
        .join(ShipmentException, ShipmentException.shipment_id == Shipment.id)
        .where(
            ShipmentException.status.in_(ACTIVE_STATUSES),
            ShipmentException.severity.in_(SERIOUS),
        )
        .group_by(Shipment.route_id)
        .subquery()
    )
    query: RouteQuery = (
        select(
            Route,
            func.coalesce(shipment_stats.c.active, 0),
            func.coalesce(shipment_stats.c.delayed, 0),
            func.coalesce(shipment_stats.c.max_delay, 0),
            func.coalesce(exception_stats.c.serious, 0),
        )
        .outerjoin(shipment_stats, shipment_stats.c.route_id == Route.id)
        .outerjoin(exception_stats, exception_stats.c.route_id == Route.id)
    )
    return query


class RouteRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_row(self, route_id: uuid.UUID, now: datetime) -> RouteRow | None:
        result = await self.session.execute(_with_stats(now).where(Route.id == route_id))
        return result.one_or_none()

    async def get_row_by_number(self, route_number: str, now: datetime) -> RouteRow | None:
        result = await self.session.execute(
            _with_stats(now).where(Route.route_number == route_number.upper())
        )
        return result.one_or_none()

    async def list(self, params: RouteListParams, now: datetime) -> tuple[Sequence[RouteRow], int]:
        query = _with_stats(now)
        if params.status:
            query = query.where(Route.status.in_(params.status))
        if params.planned_risk_level:
            query = query.where(Route.risk_level.in_(params.planned_risk_level))
        if params.origin:
            query = query.where(func.lower(Route.origin) == params.origin.lower())
        if params.destination:
            query = query.where(func.lower(Route.destination) == params.destination.lower())
        if params.search:
            query = query.where(
                contains_any(params.search, Route.route_number, Route.origin, Route.destination)
            )
        if params.delayed is not None:
            has_delayed_shipment = exists().where(
                Shipment.route_id == Route.id,
                Shipment.status != ShipmentStatus.DELIVERED,
                Shipment.estimated_delivery < now,
            )
            is_delayed = or_(Route.status == RouteStatus.DELAYED, has_delayed_shipment)
            query = query.where(is_delayed if params.delayed else not_(is_delayed))
        sort_columns: dict[str, Column] = {
            "route_number": Route.route_number,
            "distance": Route.distance_km,
            "planned_risk": _PLANNED_RISK_RANK,
        }
        query = apply_sort(query, params.sort.value, sort_columns, tiebreaker=Route.id)
        return await paginate_rows(self.session, query, params)

    async def all_active(self, now: datetime) -> Sequence[RouteRow]:
        """Every route that is not finished. The route network is small (tens of lanes), so
        ranking by the computed risk score happens in Python, where the rule lives."""
        result = await self.session.execute(
            _with_stats(now).where(
                Route.status.not_in((RouteStatus.COMPLETED, RouteStatus.CANCELLED))
            )
        )
        return result.all()
