"""Fixtures for tests that need real, *committed* data and several concurrent sessions.

The usual `session` fixture rolls everything back and uses one connection, so it cannot show
locking or race conditions. These fixtures commit for real and clean up afterwards.
"""

from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.modules.orders.models import Order
from app.modules.shipments.models import Shipment
from app.modules.warehouses.models import Warehouse
from tests.db import factories as f

SessionFactory = async_sessionmaker[AsyncSession]


@dataclass
class CommittedWorld:
    order: Order
    warehouse: Warehouse
    shipment: Shipment


@pytest.fixture
async def session_factory(test_database_url: str) -> AsyncIterator[SessionFactory]:
    engine = create_async_engine(test_database_url)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


async def cleanup(
    factory: SessionFactory, *orders: Order, warehouse: Warehouse | None = None
) -> None:
    """Delete committed test data in foreign-key order (events/exceptions cascade)."""
    async with factory() as session:
        for order in orders:
            await session.execute(delete(Shipment).where(Shipment.order_id == order.id))
            await session.execute(delete(Order).where(Order.id == order.id))
        if warehouse is not None:
            await session.execute(delete(Warehouse).where(Warehouse.id == warehouse.id))
        await session.commit()


@pytest.fixture
async def committed_world(session_factory: SessionFactory) -> AsyncIterator[CommittedWorld]:
    async with session_factory() as session:
        order, warehouse = f.make_order(), f.make_warehouse()
        session.add_all([order, warehouse])
        await session.flush()
        shipment = f.make_shipment(
            order, warehouse, created_at=datetime.now(UTC) - timedelta(hours=1)
        )
        session.add(shipment)
        await session.commit()
    yield CommittedWorld(order, warehouse, shipment)
    await cleanup(session_factory, order, warehouse=warehouse)
