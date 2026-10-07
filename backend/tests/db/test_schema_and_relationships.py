from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import inspect, select, text
from sqlalchemy.engine import Connection
from sqlalchemy.exc import InvalidRequestError
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession
from sqlalchemy.orm import selectinload

import app.models  # noqa: F401
from app.core.base import Base
from app.modules.orders.models import Order
from app.modules.shipments.models import Shipment
from app.modules.tracking.models import TrackingEvent, TrackingEventType
from tests.db import factories as f


async def test_migrations_match_models(connection: AsyncConnection) -> None:
    """Fails when a model changed without a migration (`alembic revision --autogenerate`)."""

    def diff(sync_connection: Connection) -> list[Any]:
        context = MigrationContext.configure(sync_connection, opts={"compare_type": True})
        return list(compare_metadata(context, Base.metadata))

    assert await connection.run_sync(diff) == []


async def test_pgvector_extension_is_installed(session: AsyncSession) -> None:
    assert (
        await session.scalar(text("SELECT count(*) FROM pg_extension WHERE extname = 'vector'"))
        == 1
    )


async def test_all_foreign_keys_are_indexed(connection: AsyncConnection) -> None:
    """Unindexed foreign keys make joins and cascading deletes slow."""

    def check(sync_connection: Connection) -> list[str]:
        inspector = inspect(sync_connection)
        missing: list[str] = []
        for table in inspector.get_table_names():
            indexed = [tuple(i["column_names"]) for i in inspector.get_indexes(table)]
            indexed += [tuple(u["column_names"]) for u in inspector.get_unique_constraints(table)]
            for fk in inspector.get_foreign_keys(table):
                columns = tuple(fk["constrained_columns"])
                if not any(index[: len(columns)] == columns for index in indexed):
                    missing.append(f"{table}{columns}")
        return missing

    assert await connection.run_sync(check) == []


async def test_relationships_load_with_explicit_eager_loading(session: AsyncSession) -> None:
    order, warehouse = f.make_order(), f.make_warehouse()
    session.add_all([order, warehouse])
    await session.flush()
    session.add_all([f.make_shipment(order, warehouse), f.make_shipment(order, warehouse)])
    await session.flush()
    session.expunge_all()

    loaded = await session.scalar(
        select(Order).where(Order.id == order.id).options(selectinload(Order.shipments))
    )

    assert loaded is not None
    assert len(loaded.shipments) == 2


async def test_unloaded_relationship_raises_instead_of_lazy_querying(session: AsyncSession) -> None:
    order, warehouse = f.make_order(), f.make_warehouse()
    session.add_all([order, warehouse])
    await session.flush()
    session.add(f.make_shipment(order, warehouse))
    await session.flush()
    session.expunge_all()

    loaded = await session.scalar(select(Order).where(Order.id == order.id))

    assert loaded is not None
    with pytest.raises(InvalidRequestError, match="lazy='raise'"):
        _ = loaded.shipments


async def test_tracking_events_come_back_in_time_order_with_json_details(
    session: AsyncSession,
) -> None:
    order, warehouse = f.make_order(), f.make_warehouse()
    session.add_all([order, warehouse])
    await session.flush()
    shipment = f.make_shipment(order, warehouse)
    session.add(shipment)
    await session.flush()
    now = datetime.now(UTC)
    for minutes, kind in [(30, TrackingEventType.LOADED), (0, TrackingEventType.CREATED)]:
        session.add(
            TrackingEvent(
                shipment_id=shipment.id,
                event_type=kind,
                location="Hannover",
                occurred_at=now + timedelta(minutes=minutes),
                details={"temperature_c": 4.2, "tags": ["cold"]},
            )
        )
    await session.flush()
    session.expunge_all()

    loaded = await session.scalar(
        select(Shipment)
        .where(Shipment.id == shipment.id)
        .options(selectinload(Shipment.tracking_events))
    )

    assert loaded is not None
    assert [e.event_type for e in loaded.tracking_events] == [
        TrackingEventType.CREATED,
        TrackingEventType.LOADED,
    ]
    assert loaded.tracking_events[0].details == {"temperature_c": 4.2, "tags": ["cold"]}
