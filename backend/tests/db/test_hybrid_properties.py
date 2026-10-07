"""The Python and SQL sides of each hybrid property must agree on every input.

If someone changes a rule in `rules.py` but not the SQL expression (or vice versa), the API
would report different answers depending on whether a value was filtered in SQL or computed in
Python. These tests catch that drift.
"""

import itertools

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.inventory.models import InventoryItem
from app.modules.warehouses.models import Warehouse
from tests.db import factories as f


async def test_inventory_hybrids_agree_with_sql(session: AsyncSession) -> None:
    warehouse = f.make_warehouse()
    session.add(warehouse)
    await session.flush()
    # Every combination around the boundaries (empty, at threshold, above, no threshold).
    for quantity, reserved, threshold in itertools.product([0, 5, 10, 11, 20], [0, 5], [0, 10]):
        if reserved <= quantity:
            session.add(
                f.make_inventory_item(
                    warehouse,
                    quantity=quantity,
                    reserved_quantity=reserved,
                    reorder_threshold=threshold,
                )
            )
    await session.flush()

    rows = await session.execute(
        select(
            InventoryItem,
            InventoryItem.available_quantity,
            InventoryItem.stock_status,
            InventoryItem.coverage_ratio,
        ).where(InventoryItem.warehouse_id == warehouse.id)
    )

    checked = 0
    for item, sql_available, sql_status, sql_coverage in rows:
        assert item.available_quantity == sql_available
        assert item.stock_status == sql_status
        if item.coverage_ratio is None:
            assert sql_coverage is None
        else:
            assert sql_coverage == pytest.approx(item.coverage_ratio)
            assert isinstance(sql_coverage, float)  # not Decimal
        checked += 1
    assert checked > 10


@pytest.mark.parametrize("used", [0, 849, 850, 949, 950, 1000])
async def test_warehouse_hybrids_agree_with_sql(session: AsyncSession, used: int) -> None:
    warehouse = f.make_warehouse(capacity=1000, current_utilization=used)
    session.add(warehouse)
    await session.flush()

    sql_pct, sql_level = (
        await session.execute(
            select(Warehouse.utilization_pct, Warehouse.utilization_level).where(
                Warehouse.id == warehouse.id
            )
        )
    ).one()

    assert sql_pct == pytest.approx(warehouse.utilization_pct)
    assert isinstance(sql_pct, float)
    assert sql_level == warehouse.utilization_level
