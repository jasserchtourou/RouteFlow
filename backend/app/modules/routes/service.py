"""Route use cases: status, live statistics and risk ranking."""

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.core.pagination import Page
from app.modules.routes import rules
from app.modules.routes.models import RiskLevel
from app.modules.routes.repository import RouteRepository, RouteRow
from app.modules.routes.schemas import (
    AtRiskParams,
    RiskAssessmentRead,
    RouteDetail,
    RouteListParams,
    RouteRead,
)
from app.modules.shipments.models import ShipmentStatus
from app.modules.shipments.schemas import ShipmentListParams, ShipmentSort
from app.modules.shipments.service import ShipmentService

ACTIVE_SHIPMENT_STATUSES = [s for s in ShipmentStatus if s != ShipmentStatus.DELIVERED]
RISK_ORDER = list(RiskLevel)


def to_read(row: RouteRow) -> RouteRead:
    route, active, delayed, max_delay, serious = row
    assessment = rules.assess_route_risk(
        rules.RouteSignals(
            planned_risk=route.risk_level,
            status=route.status,
            active_shipments=active,
            delayed_shipments=delayed,
            max_delay_minutes=max_delay,
            serious_exceptions=serious,
        )
    )
    return RouteRead(
        id=route.id,
        route_number=route.route_number,
        origin=route.origin,
        destination=route.destination,
        distance_km=route.distance_km,
        estimated_duration_minutes=route.estimated_duration_minutes,
        status=route.status,
        planned_risk_level=route.risk_level,
        active_shipments=active,
        delayed_shipments=delayed,
        max_delay_minutes=max_delay,
        serious_exceptions=serious,
        risk=RiskAssessmentRead(
            score=assessment.score, level=assessment.level, factors=assessment.factors
        ),
    )


class RouteService:
    def __init__(self, session: AsyncSession) -> None:
        self.routes = RouteRepository(session)
        self.shipments = ShipmentService(session)

    async def list(self, params: RouteListParams) -> Page[RouteRead]:
        rows, total = await self.routes.list(params, datetime.now(UTC))
        return Page[RouteRead](
            items=[to_read(row) for row in rows],
            total=total,
            limit=params.limit,
            offset=params.offset,
        )

    async def detail(self, route_id: uuid.UUID) -> RouteDetail:
        row = await self.routes.get_row(route_id, datetime.now(UTC))
        return await self._detail(row, str(route_id))

    async def detail_by_number(self, route_number: str) -> RouteDetail:
        row = await self.routes.get_row_by_number(route_number, datetime.now(UTC))
        return await self._detail(row, route_number)

    async def at_risk(self, params: AtRiskParams) -> Sequence[RouteRead]:
        """Routes the dispatcher should look at first: highest computed risk score first."""
        minimum = RISK_ORDER.index(params.min_level)
        assessed = [to_read(row) for row in await self.routes.all_active(datetime.now(UTC))]
        relevant = [r for r in assessed if RISK_ORDER.index(r.risk.level) >= minimum]
        relevant.sort(key=lambda r: (-r.risk.score, -r.delayed_shipments, r.route_number))
        return relevant[: params.limit]

    async def _detail(self, row: RouteRow | None, reference: str) -> RouteDetail:
        if row is None:
            raise NotFoundError(f"Route {reference} not found", details={"route": reference})
        route = to_read(row)
        shipments = await self.shipments.list(
            ShipmentListParams(
                route_number=route.route_number,
                status=ACTIVE_SHIPMENT_STATUSES,
                sort=ShipmentSort.ESTIMATED_DELIVERY,
                limit=100,
            )
        )
        return RouteDetail(**route.model_dump(), shipments=shipments.items)
