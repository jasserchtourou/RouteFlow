"""HTTP layer for the operations dashboard."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.dependencies import AppSettings, DbSession
from app.core.clock import Clock
from app.modules.dashboard.schemas import DashboardOverview
from app.modules.dashboard.service import DashboardService

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def get_dashboard_service(session: DbSession, settings: AppSettings) -> DashboardService:
    return DashboardService(session, settings.business_timezone)


Service = Annotated[DashboardService, Depends(get_dashboard_service)]


@router.get(
    "/overview",
    response_model=DashboardOverview,
    summary="Network-wide KPIs: orders, shipments, exceptions, fleet, warehouses, delivery",
)
async def dashboard_overview(service: Service, clock: Clock) -> DashboardOverview:
    return await service.overview(clock())
