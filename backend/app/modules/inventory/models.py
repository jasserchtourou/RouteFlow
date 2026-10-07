from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    ColumnElement,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    case,
    cast,
    func,
)
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.modules.inventory import rules
from app.modules.inventory.rules import StockStatus

if TYPE_CHECKING:
    from app.modules.warehouses.models import Warehouse


class InventoryItem(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "inventory_items"
    __table_args__ = (
        UniqueConstraint("warehouse_id", "sku", name="uq_inventory_items_warehouse_sku"),
        CheckConstraint("quantity >= 0", name="quantity_non_negative"),
        CheckConstraint("reserved_quantity >= 0", name="reserved_non_negative"),
        CheckConstraint("reserved_quantity <= quantity", name="reserved_within_quantity"),
        CheckConstraint("reorder_threshold >= 0", name="threshold_non_negative"),
        Index("ix_inventory_items_sku", "sku"),
    )

    # The unique (warehouse_id, sku) index also serves lookups by warehouse_id alone.
    warehouse_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("warehouses.id", ondelete="CASCADE"))
    sku: Mapped[str] = mapped_column(String(32))
    product_name: Mapped[str] = mapped_column(String(160))
    quantity: Mapped[int] = mapped_column(Integer)
    reserved_quantity: Mapped[int] = mapped_column(Integer, default=0)
    reorder_threshold: Mapped[int] = mapped_column(Integer)

    warehouse: Mapped[Warehouse] = relationship(back_populates="inventory_items", lazy="raise")

    # Hybrid properties: one definition usable on instances (Python) and in queries (SQL),
    # e.g. `item.stock_status` and `select(...).where(InventoryItem.stock_status == "LOW")`.

    @hybrid_property
    def available_quantity(self) -> int:
        return rules.available_quantity(self.quantity, self.reserved_quantity)

    @available_quantity.inplace.expression
    @classmethod
    def _available_quantity_expression(cls) -> ColumnElement[int]:
        return cls.quantity - cls.reserved_quantity

    @hybrid_property
    def stock_status(self) -> StockStatus:
        return rules.stock_status(self.available_quantity, self.reorder_threshold)

    @stock_status.inplace.expression
    @classmethod
    def _stock_status_expression(cls) -> ColumnElement[str]:
        available = cls.quantity - cls.reserved_quantity
        return case(
            (available <= 0, StockStatus.OUT_OF_STOCK.value),
            (available <= cls.reorder_threshold, StockStatus.LOW.value),
            else_=StockStatus.OK.value,
        )

    @hybrid_property
    def coverage_ratio(self) -> float | None:
        return rules.coverage_ratio(self.available_quantity, self.reorder_threshold)

    @coverage_ratio.inplace.expression
    @classmethod
    def _coverage_ratio_expression(cls) -> ColumnElement[float | None]:
        available = cls.quantity - cls.reserved_quantity
        return cast(available / func.nullif(cast(cls.reorder_threshold, Float), 0), Float)
