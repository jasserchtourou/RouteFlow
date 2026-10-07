"""Inventory read use cases."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import Page
from app.modules.inventory import rules
from app.modules.inventory.repository import InventoryRepository
from app.modules.inventory.schemas import (
    InventoryItemRead,
    InventoryListParams,
    LowStockItemRead,
    LowStockParams,
)
from app.modules.warehouses.service import WarehouseService


class InventoryService:
    def __init__(self, session: AsyncSession) -> None:
        self.inventory = InventoryRepository(session)
        # Cross-module access goes through the other module's service, not its repository.
        self.warehouses = WarehouseService(session)

    async def list_for_warehouse(
        self, warehouse_id: uuid.UUID, params: InventoryListParams
    ) -> Page[InventoryItemRead]:
        warehouse = await self.warehouses.get(warehouse_id)  # 404 for unknown warehouses
        items, total = await self.inventory.list_for_warehouse(warehouse.id, params)
        return Page[InventoryItemRead](
            items=[InventoryItemRead.model_validate(item) for item in items],
            total=total,
            limit=params.limit,
            offset=params.offset,
        )

    async def low_stock(self, params: LowStockParams) -> Page[LowStockItemRead]:
        rows, total = await self.inventory.list_low_stock(params)
        items = [
            LowStockItemRead(
                **InventoryItemRead.model_validate(item).model_dump(),
                warehouse_code=code,
                warehouse_name=name,
                shortfall=rules.shortfall(item.available_quantity, item.reorder_threshold),
            )
            for item, code, name in rows
        ]
        return Page[LowStockItemRead](
            items=items, total=total, limit=params.limit, offset=params.offset
        )
