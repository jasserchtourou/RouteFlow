"""HTTP layer for the yard (3D site view data)."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.dependencies import AppSettings, DbSession
from app.core.clock import Clock
from app.core.errors import error_responses
from app.modules.yard.schemas import SceneRead
from app.modules.yard.service import YardService

router = APIRouter(prefix="/warehouses", tags=["yard"])


def get_yard_service(session: DbSession, settings: AppSettings) -> YardService:
    return YardService(
        session, settings.business_timezone, simulation_enabled=settings.yard_simulation_enabled
    )


Service = Annotated[YardService, Depends(get_yard_service)]


@router.get(
    "/{warehouse_id}/scene",
    response_model=SceneRead,
    responses=error_responses(404),
    summary="Site scene: docks, trucks, forklifts, pallets and KPIs for the 3D view",
)
async def warehouse_scene(warehouse_id: uuid.UUID, service: Service, clock: Clock) -> SceneRead:
    return await service.scene(warehouse_id, clock())
