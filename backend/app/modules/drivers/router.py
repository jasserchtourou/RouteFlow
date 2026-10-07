"""HTTP layer for drivers."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import DbSession
from app.core.errors import error_responses
from app.core.pagination import Page
from app.modules.drivers.schemas import DriverListParams, DriverRead
from app.modules.drivers.service import DriverService

router = APIRouter(prefix="/drivers", tags=["fleet"])


def get_driver_service(session: DbSession) -> DriverService:
    return DriverService(session)


Service = Annotated[DriverService, Depends(get_driver_service)]


@router.get("", response_model=Page[DriverRead], summary="List drivers")
async def list_drivers(
    params: Annotated[DriverListParams, Query()], service: Service
) -> Page[DriverRead]:
    return await service.list(params)


@router.get(
    "/{driver_id}", response_model=DriverRead, responses=error_responses(404), summary="Driver"
)
async def get_driver(driver_id: uuid.UUID, service: Service) -> DriverRead:
    return await service.get(driver_id)
