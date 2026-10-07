import uuid
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from app.core.pagination import PageParams
from app.core.types import SearchTerm, WarehouseCode
from app.modules.inventory.rules import StockStatus


class InventoryItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    warehouse_id: uuid.UUID
    sku: str
    product_name: str
    quantity: int
    reserved_quantity: int
    available_quantity: int
    reorder_threshold: int
    stock_status: StockStatus
    coverage_ratio: float | None = Field(
        description="Available / reorder threshold; below 1.0 means reorder needed"
    )
    updated_at: datetime

    @field_serializer("coverage_ratio")
    def _round_ratio(self, value: float | None) -> float | None:
        return None if value is None else round(value, 2)


class LowStockItemRead(InventoryItemRead):
    warehouse_code: str
    warehouse_name: str
    shortfall: int = Field(description="Units needed to get back above the reorder threshold")


class InventorySort(StrEnum):
    SKU = "sku"
    PRODUCT_NAME = "product_name"
    AVAILABLE = "available"
    AVAILABLE_DESC = "-available"
    COVERAGE = "coverage"  # most urgent first


class InventoryListParams(PageParams):
    model_config = ConfigDict(extra="forbid")

    stock_status: list[StockStatus] | None = Field(default=None, description="Repeatable")
    search: SearchTerm | None = Field(default=None, description="Substring of SKU or product")
    sort: InventorySort = InventorySort.SKU


class LowStockParams(PageParams):
    """Items that need attention across all warehouses, most urgent first by default."""

    model_config = ConfigDict(extra="forbid")

    warehouse_code: list[WarehouseCode] | None = Field(default=None, description="e.g. WH-GAR")
    include_out_of_stock: bool = True
    sort: InventorySort = InventorySort.COVERAGE
