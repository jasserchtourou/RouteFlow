"""Two scanners report the same step for the same shipment at the same moment."""

import asyncio

import pytest
from sqlalchemy import func, select

from app.modules.shipments.models import ShipmentStatus
from app.modules.shipments.rules import InvalidShipmentTransitionError
from app.modules.tracking.models import TrackingEvent, TrackingEventType
from app.modules.tracking.schemas import TrackingEventCreate
from app.modules.tracking.service import TrackingService
from tests.db.conftest import CommittedWorld, SessionFactory


async def test_row_lock_serializes_concurrent_events(
    session_factory: SessionFactory, committed_world: CommittedWorld
) -> None:
    shipment_id = committed_world.shipment.id
    picked = TrackingEventCreate(event_type=TrackingEventType.PICKED, location="Scanner")

    async with session_factory() as first, session_factory() as second:
        # Scanner A takes the row lock and is "busy" for a moment.
        tracking_a = TrackingService(first)
        await tracking_a.shipments.lock(shipment_id)

        # Scanner B starts the same transition and must wait for A's lock.
        scanner_b = asyncio.create_task(TrackingService(second).record(shipment_id, picked))
        await asyncio.sleep(0.3)
        assert not scanner_b.done(), "B should be blocked by A's row lock"

        # A records PICKED (re-locking its own row is a no-op) and commits, releasing the lock.
        result_a = await tracking_a.record(shipment_id, picked)
        assert result_a.shipment.status == ShipmentStatus.PICKED

        # B now sees the new state, PICKED -> PICKED is not a valid next step.
        with pytest.raises(InvalidShipmentTransitionError):
            await scanner_b

    async with session_factory() as check:
        stored = await check.scalar(
            select(func.count())
            .select_from(TrackingEvent)
            .where(
                TrackingEvent.shipment_id == shipment_id,
                TrackingEvent.event_type == TrackingEventType.PICKED,
            )
        )
        assert stored == 1  # exactly one PICKED stored, no duplicate
