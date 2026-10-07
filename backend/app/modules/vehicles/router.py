"""HTTP layer for vehicles and the fleet overview."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import DbSession
from app.core.errors import error_responses
from app.core.pagination import Page
from app.modules.vehicles.schemas import FleetOverview, VehicleListParams, VehicleRead
from app.modules.vehicles.service import VehicleService

router = APIRouter(tags=["fleet"])


def get_vehicle_service(session: DbSession) -> VehicleService:
    return VehicleService(session)


Service = Annotated[VehicleService, Depends(get_vehicle_service)]


@router.get("/fleet/overview", response_model=FleetOverview, summary="Fleet status at a glance")
async def fleet_overview(service: Service) -> FleetOverview:
    return await service.overview()


@router.get("/vehicles", response_model=Page[VehicleRead], summary="List vehicles")
async def list_vehicles(
    params: Annotated[VehicleListParams, Query()], service: Service
) -> Page[VehicleRead]:
    return await service.list(params)


@router.get(
    "/vehicles/by-registration/{registration}",
    response_model=VehicleRead,
    responses=error_responses(404),
    summary="Vehicle by registration plate (e.g. HH-RF 1592)",
)
async def get_vehicle_by_registration(registration: str, service: Service) -> VehicleRead:
    return await service.get_by_registration(registration)


@router.get(
    "/vehicles/{vehicle_id}",
    response_model=VehicleRead,
    responses=error_responses(404),
    summary="Vehicle status, current location, driver and load",
)
async def get_vehicle(vehicle_id: uuid.UUID, service: Service) -> VehicleRead:
    return await service.get(vehicle_id)
