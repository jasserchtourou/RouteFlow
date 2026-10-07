"""HTTP layer for warehouses (read-only for now)."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import DbSession
from app.core.errors import error_responses
from app.core.pagination import Page
from app.modules.warehouses.schemas import (
    DockRead,
    EquipmentRead,
    WarehouseDetail,
    WarehouseListItem,
    WarehouseListParams,
)
from app.modules.warehouses.service import WarehouseService

router = APIRouter(prefix="/warehouses", tags=["warehouses"])


def get_warehouse_service(session: DbSession) -> WarehouseService:
    return WarehouseService(session)


Service = Annotated[WarehouseService, Depends(get_warehouse_service)]


@router.get("", response_model=Page[WarehouseListItem], summary="List warehouses")
async def list_warehouses(
    params: Annotated[WarehouseListParams, Query()], service: Service
) -> Page[WarehouseListItem]:
    return await service.list(params)


@router.get(
    "/by-code/{code}",
    response_model=WarehouseDetail,
    responses=error_responses(404),
    summary="Warehouse details by code (e.g. WH-GAR)",
)
async def get_warehouse_by_code(code: str, service: Service) -> WarehouseDetail:
    return await service.detail(await service.get_by_code(code))


@router.get(
    "/{warehouse_id}",
    response_model=WarehouseDetail,
    responses=error_responses(404),
    summary="Warehouse details with inventory, dock and equipment summaries",
)
async def get_warehouse(warehouse_id: uuid.UUID, service: Service) -> WarehouseDetail:
    return await service.detail(await service.get(warehouse_id))


@router.get(
    "/{warehouse_id}/docks",
    response_model=list[DockRead],
    responses=error_responses(404),
    summary="Dock doors in facade order",
)
async def list_docks(warehouse_id: uuid.UUID, service: Service) -> list[DockRead]:
    return [DockRead.model_validate(dock) for dock in await service.docks(warehouse_id)]


@router.get(
    "/{warehouse_id}/equipment",
    response_model=list[EquipmentRead],
    responses=error_responses(404),
    summary="Material-handling equipment on site",
)
async def list_equipment(warehouse_id: uuid.UUID, service: Service) -> list[EquipmentRead]:
    return [EquipmentRead.model_validate(item) for item in await service.equipment(warehouse_id)]
