from datetime import UTC, datetime

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.exceptions.models import ExceptionType, ShipmentException
from app.modules.inventory.models import InventoryItem
from app.modules.orders.models import Order
from app.modules.shipments.models import Shipment, ShipmentStatus, TemperatureStatus
from app.modules.tracking.models import TrackingEvent
from app.modules.warehouses.models import Dock, DockStatus, Warehouse, WarehouseStatus
from app.seed.generator import generate
from app.seed.runner import DatabaseNotEmptyError, seed_database

NOW = datetime(2026, 10, 6, 12, 0, tzinfo=UTC)


async def _count(session: AsyncSession, model: type) -> int:
    return await session.scalar(select(func.count()).select_from(model)) or 0


def test_generation_is_deterministic() -> None:
    first, second = generate(NOW, seed=7), generate(NOW, seed=7)

    assert [s.id for s in first.shipments] == [s.id for s in second.shipments]
    assert [e.occurred_at for e in first.events] == [e.occurred_at for e in second.events]


def test_site_infrastructure_does_not_reshuffle_other_data() -> None:
    """Docks/equipment use their own random stream, so shipments stay stable across changes."""
    data = generate(NOW, seed=42)

    assert len(data.docks) > 0
    assert len(data.equipment) > 0
    assert len(data.events) == 652
    assert len(data.exceptions) == 21


def test_different_seeds_give_different_data() -> None:
    assert generate(NOW, seed=1).shipments[0].id != generate(NOW, seed=2).shipments[0].id


async def test_seed_populates_every_table_consistently(session: AsyncSession) -> None:
    data = await seed_database(session, now=NOW)

    assert await _count(session, Warehouse) == len(data.warehouses) == 7
    assert await _count(session, Shipment) == len(data.shipments)
    assert await _count(session, TrackingEvent) == len(data.events)
    # Every shipment has an order, and every non-backlog order has exactly one shipment.
    assert await _count(session, Order) > await _count(session, Shipment)
    assert await _count(session, InventoryItem) > 0


async def test_seed_refuses_to_overwrite_existing_data(session: AsyncSession) -> None:
    await seed_database(session, now=NOW)

    with pytest.raises(DatabaseNotEmptyError):
        await seed_database(session, now=NOW)


async def test_seed_reset_replaces_existing_data(session: AsyncSession) -> None:
    await seed_database(session, now=NOW, seed=1)
    await seed_database(session, now=NOW, seed=2, reset=True)

    assert await _count(session, Shipment) == 110  # replaced, not doubled


async def test_scripted_scenarios_exist(session: AsyncSession) -> None:
    await seed_database(session, now=NOW)

    shp_2211 = await session.scalar(select(Shipment).where(Shipment.shipment_number == "SHP-2211"))
    assert shp_2211 is not None
    assert shp_2211.status == ShipmentStatus.IN_TRANSIT
    assert shp_2211.temperature_status == TemperatureStatus.DEVIATION
    assert shp_2211.estimated_delivery < NOW  # already late
    kinds = await session.scalars(
        select(ShipmentException.type).where(ShipmentException.shipment_id == shp_2211.id)
    )
    assert {ExceptionType.DELAYED, ExceptionType.TEMPERATURE_DEVIATION} <= set(kinds)

    garbsen = await session.scalar(select(Warehouse).where(Warehouse.code == "WH-GAR"))
    assert garbsen is not None
    assert garbsen.status == WarehouseStatus.DISRUPTED
    assert garbsen.utilization_level == "CRITICAL"
    broken_docks = await session.scalar(
        select(func.count())
        .select_from(Dock)
        .where(Dock.warehouse_id == garbsen.id, Dock.status == DockStatus.OUT_OF_SERVICE)
    )
    assert broken_docks == 2


async def test_event_timeline_is_never_in_the_future(session: AsyncSession) -> None:
    await seed_database(session, now=NOW)

    latest = await session.scalar(select(func.max(TrackingEvent.occurred_at)))

    assert latest is not None
    assert latest <= NOW
