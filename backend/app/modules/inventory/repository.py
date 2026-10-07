"""Data access for inventory items."""

import uuid
from collections.abc import Sequence

from sqlalchemy import Row, Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.querying import Column, apply_sort, contains_any, paginate, paginate_rows
from app.modules.inventory.models import InventoryItem
from app.modules.inventory.rules import StockStatus
from app.modules.inventory.schemas import InventoryListParams, LowStockParams
from app.modules.warehouses.models import Warehouse

_SORT_COLUMNS: dict[str, Column] = {
    "sku": InventoryItem.sku,
    "product_name": InventoryItem.product_name,
    "available": InventoryItem.available_quantity,
    "coverage": InventoryItem.coverage_ratio,
}

LowStockRow = Row[InventoryItem, str, str]


class InventoryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_for_warehouse(
        self, warehouse_id: uuid.UUID, params: InventoryListParams
    ) -> tuple[Sequence[InventoryItem], int]:
        query = select(InventoryItem).where(InventoryItem.warehouse_id == warehouse_id)
        if params.stock_status:
            query = query.where(InventoryItem.stock_status.in_(params.stock_status))
        if params.search:
            query = query.where(
                contains_any(params.search, InventoryItem.sku, InventoryItem.product_name)
            )
        query = apply_sort(query, params.sort.value, _SORT_COLUMNS, tiebreaker=InventoryItem.id)
        return await paginate(self.session, query, params)

    async def list_low_stock(self, params: LowStockParams) -> tuple[Sequence[LowStockRow], int]:
        statuses = [StockStatus.LOW]
        if params.include_out_of_stock:
            statuses.append(StockStatus.OUT_OF_STOCK)
        query: Select[InventoryItem, str, str] = (
            select(InventoryItem, Warehouse.code, Warehouse.name)
            .join(Warehouse, Warehouse.id == InventoryItem.warehouse_id)
            .where(InventoryItem.stock_status.in_(statuses))
        )
        if params.warehouse_code:
            query = query.where(Warehouse.code.in_(params.warehouse_code))
        query = apply_sort(query, params.sort.value, _SORT_COLUMNS, tiebreaker=InventoryItem.id)
        return await paginate_rows(self.session, query, params)
