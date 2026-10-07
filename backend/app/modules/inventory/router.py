"""HTTP layer for inventory (read-only for now)."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import DbSession
from app.core.errors import error_responses
from app.core.pagination import Page
from app.modules.inventory.schemas import (
    InventoryItemRead,
    InventoryListParams,
    LowStockItemRead,
    LowStockParams,
)
from app.modules.inventory.service import InventoryService

router = APIRouter(tags=["inventory"])


def get_inventory_service(session: DbSession) -> InventoryService:
    return InventoryService(session)


Service = Annotated[InventoryService, Depends(get_inventory_service)]


@router.get(
    "/warehouses/{warehouse_id}/inventory",
    response_model=Page[InventoryItemRead],
    responses=error_responses(404),
    summary="Inventory of one warehouse",
)
async def list_warehouse_inventory(
    warehouse_id: uuid.UUID, params: Annotated[InventoryListParams, Query()], service: Service
) -> Page[InventoryItemRead]:
    return await service.list_for_warehouse(warehouse_id, params)


@router.get(
    "/inventory/low-stock",
    response_model=Page[LowStockItemRead],
    summary="Items at or below their reorder threshold, across warehouses",
)
async def list_low_stock(
    params: Annotated[LowStockParams, Query()], service: Service
) -> Page[LowStockItemRead]:
    return await service.low_stock(params)
