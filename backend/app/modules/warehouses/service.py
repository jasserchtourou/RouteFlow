"""Warehouse read use cases."""

import uuid
from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.core.pagination import Page
from app.modules.warehouses.models import Dock, Equipment, Warehouse
from app.modules.warehouses.repository import WarehouseRepository
from app.modules.warehouses.schemas import (
    WarehouseDetail,
    WarehouseListItem,
    WarehouseListParams,
    WarehouseRead,
)


class WarehouseService:
    def __init__(self, session: AsyncSession) -> None:
        self.warehouses = WarehouseRepository(session)

    async def list(self, params: WarehouseListParams) -> Page[WarehouseListItem]:
        rows, total = await self.warehouses.list(params)
        items = [
            WarehouseListItem(
                **WarehouseRead.model_validate(warehouse).model_dump(),
                sku_count=sku_count,
                low_stock_count=low_stock_count,
            )
            for warehouse, sku_count, low_stock_count in rows
        ]
        return Page[WarehouseListItem](
            items=items, total=total, limit=params.limit, offset=params.offset
        )

    async def get(self, warehouse_id: uuid.UUID) -> Warehouse:
        warehouse = await self.warehouses.get(warehouse_id)
        if warehouse is None:
            raise NotFoundError(
                f"Warehouse {warehouse_id} not found", details={"id": str(warehouse_id)}
            )
        return warehouse

    async def get_by_code(self, code: str) -> Warehouse:
        warehouse = await self.warehouses.get_by_code(code)
        if warehouse is None:
            raise NotFoundError(f"Warehouse {code} not found", details={"code": code})
        return warehouse

    async def detail(self, warehouse: Warehouse) -> WarehouseDetail:
        return WarehouseDetail(
            **WarehouseRead.model_validate(warehouse).model_dump(),
            inventory=await self.warehouses.inventory_summary(warehouse.id),
            docks=await self.warehouses.dock_summary(warehouse.id),
            equipment=await self.warehouses.equipment_summary(warehouse.id),
        )

    async def docks(self, warehouse_id: uuid.UUID) -> Sequence[Dock]:
        return await self.warehouses.docks((await self.get(warehouse_id)).id)

    async def equipment(self, warehouse_id: uuid.UUID) -> Sequence[Equipment]:
        return await self.warehouses.equipment((await self.get(warehouse_id)).id)
