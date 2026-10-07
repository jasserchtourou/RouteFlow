"""Data access for warehouses and their site infrastructure (docks, equipment).

Read-model queries here may aggregate over inventory rows; writes to inventory still belong to
the inventory module.
"""

import uuid
from collections.abc import Sequence

from sqlalchemy import Row, Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.querying import Column, apply_sort, contains_any, paginate_rows
from app.modules.inventory.models import InventoryItem
from app.modules.inventory.rules import StockStatus
from app.modules.warehouses.models import (
    Dock,
    DockDirection,
    DockStatus,
    Equipment,
    EquipmentStatus,
    Warehouse,
)
from app.modules.warehouses.schemas import (
    DockSummary,
    EquipmentSummary,
    InventorySummary,
    WarehouseListParams,
)

NEEDS_REORDER = (StockStatus.LOW.value, StockStatus.OUT_OF_STOCK.value)

# Per-warehouse inventory counts, joined onto the warehouse list in one query (no N+1).
_inventory_stats = (
    select(
        InventoryItem.warehouse_id,
        func.count().label("sku_count"),
        func.count().filter(InventoryItem.stock_status.in_(NEEDS_REORDER)).label("low_stock"),
    )
    .group_by(InventoryItem.warehouse_id)
    .subquery()
)
_SKU_COUNT = func.coalesce(_inventory_stats.c.sku_count, 0)
_LOW_STOCK_COUNT = func.coalesce(_inventory_stats.c.low_stock, 0)

_SORT_COLUMNS: dict[str, Column] = {
    "code": Warehouse.code,
    "name": Warehouse.name,
    "utilization": Warehouse.utilization_pct,
    "low_stock": _LOW_STOCK_COUNT,
}

WarehouseRow = Row[Warehouse, int, int]


class WarehouseRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, warehouse_id: uuid.UUID) -> Warehouse | None:
        return await self.session.get(Warehouse, warehouse_id)

    async def get_by_code(self, code: str) -> Warehouse | None:
        return await self.session.scalar(select(Warehouse).where(Warehouse.code == code.upper()))

    async def list(self, params: WarehouseListParams) -> tuple[Sequence[WarehouseRow], int]:
        query: Select[Warehouse, int, int] = select(
            Warehouse, _SKU_COUNT, _LOW_STOCK_COUNT
        ).outerjoin(_inventory_stats, _inventory_stats.c.warehouse_id == Warehouse.id)
        if params.status:
            query = query.where(Warehouse.status.in_(params.status))
        if params.utilization_level:
            query = query.where(Warehouse.utilization_level.in_(params.utilization_level))
        if params.location:
            query = query.where(func.lower(Warehouse.location) == params.location.lower())
        if params.search:
            query = query.where(contains_any(params.search, Warehouse.code, Warehouse.name))
        query = apply_sort(query, params.sort.value, _SORT_COLUMNS, tiebreaker=Warehouse.id)
        return await paginate_rows(self.session, query, params)

    async def inventory_summary(self, warehouse_id: uuid.UUID) -> InventorySummary:
        row = (
            await self.session.execute(
                select(
                    func.count(),
                    func.coalesce(func.sum(InventoryItem.quantity), 0),
                    func.coalesce(func.sum(InventoryItem.reserved_quantity), 0),
                    func.count().filter(InventoryItem.stock_status.in_(NEEDS_REORDER)),
                    func.count().filter(
                        InventoryItem.stock_status == StockStatus.OUT_OF_STOCK.value
                    ),
                ).where(InventoryItem.warehouse_id == warehouse_id)
            )
        ).one()
        skus, quantity, reserved, low, out = row
        return InventorySummary(
            sku_count=skus,
            total_quantity=quantity,
            reserved_quantity=reserved,
            available_quantity=quantity - reserved,
            low_stock_count=low,
            out_of_stock_count=out,
        )

    async def dock_summary(self, warehouse_id: uuid.UUID) -> DockSummary:
        row = (
            await self.session.execute(
                select(
                    func.count(),
                    func.count().filter(Dock.direction == DockDirection.INBOUND),
                    func.count().filter(Dock.direction == DockDirection.OUTBOUND),
                    func.count().filter(Dock.status == DockStatus.OUT_OF_SERVICE),
                ).where(Dock.warehouse_id == warehouse_id)
            )
        ).one()
        total, inbound, outbound, out_of_service = row
        return DockSummary(
            total=total, inbound=inbound, outbound=outbound, out_of_service=out_of_service
        )

    async def equipment_summary(self, warehouse_id: uuid.UUID) -> EquipmentSummary:
        rows = await self.session.execute(
            select(Equipment.status, func.count())
            .where(Equipment.warehouse_id == warehouse_id)
            .group_by(Equipment.status)
        )
        by_status = dict.fromkeys(EquipmentStatus, 0) | dict(rows.all())
        return EquipmentSummary(total=sum(by_status.values()), by_status=by_status)

    async def docks(self, warehouse_id: uuid.UUID) -> Sequence[Dock]:
        result = await self.session.scalars(
            select(Dock).where(Dock.warehouse_id == warehouse_id).order_by(Dock.position)
        )
        return result.all()

    async def equipment(self, warehouse_id: uuid.UUID) -> Sequence[Equipment]:
        result = await self.session.scalars(
            select(Equipment)
            .where(Equipment.warehouse_id == warehouse_id)
            .order_by(Equipment.equipment_type, Equipment.code)
        )
        return result.all()
