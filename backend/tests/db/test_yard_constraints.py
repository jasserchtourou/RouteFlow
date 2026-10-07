"""The database rejects impossible truck visits, independent of the simulator."""

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.warehouses.models import Dock, Warehouse
from app.modules.yard.models import DockAppointment
from tests.db import factories as f

T0 = datetime(2026, 10, 7, 12, 0, tzinfo=UTC)


async def _dock(session: AsyncSession) -> tuple[Warehouse, Dock]:
    warehouse = f.make_warehouse()
    session.add(warehouse)
    await session.flush()
    dock = f.make_dock(warehouse)
    session.add(dock)
    await session.flush()
    return warehouse, dock


def _visit(warehouse: Warehouse, dock: Dock, **overrides: Any) -> DockAppointment:
    values: dict[str, Any] = {
        "warehouse_id": warehouse.id,
        "dock_id": dock.id,
        "sequence": 0,
        "truck_code": "TRK-2001",
        "carrier": "Test Carrier",
        "direction": dock.direction,
        "arrives_at": T0,
        "docked_at": T0 + timedelta(minutes=3),
        "departs_at": T0 + timedelta(minutes=20),
        "pallets_total": 8,
    }
    return DockAppointment(**{**values, **overrides})


async def test_a_valid_visit_is_stored(session: AsyncSession) -> None:
    warehouse, dock = await _dock(session)
    visit = _visit(warehouse, dock)
    session.add(visit)
    await session.flush()
    assert visit.id is not None
    assert visit.created_at is not None


@pytest.mark.parametrize(
    ("overrides", "constraint"),
    [
        ({"docked_at": T0 - timedelta(minutes=1)}, "timeline_ordered"),  # docks before arriving
        ({"departs_at": T0 + timedelta(minutes=3)}, "timeline_ordered"),  # leaves on docking
        ({"pallets_total": 0}, "pallets_positive"),
        ({"sequence": -1}, "sequence_non_negative"),
    ],
)
async def test_impossible_visits_are_rejected(
    session: AsyncSession, overrides: dict[str, Any], constraint: str
) -> None:
    warehouse, dock = await _dock(session)
    session.add(_visit(warehouse, dock, **overrides))
    with pytest.raises(IntegrityError, match=constraint):
        await session.flush()


async def test_a_dock_cannot_have_two_visits_with_the_same_sequence(session: AsyncSession) -> None:
    warehouse, dock = await _dock(session)
    session.add_all([_visit(warehouse, dock), _visit(warehouse, dock, truck_code="TRK-2002")])
    with pytest.raises(IntegrityError, match="uq_dock_appointments_dock_sequence"):
        await session.flush()


async def test_deleting_a_dock_removes_its_visits(session: AsyncSession) -> None:
    warehouse, dock = await _dock(session)
    session.add(_visit(warehouse, dock))
    await session.flush()

    await session.execute(delete(Dock).where(Dock.id == dock.id))

    remaining = await session.scalar(select(func.count()).select_from(DockAppointment))
    assert remaining == 0
