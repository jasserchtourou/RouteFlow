"""Race conditions in the write paths, reproduced with real concurrent transactions.

Each test lets session A do part of its work *without committing*, starts session B on the
same data, proves B has to wait, and then lets A finish.
"""

import asyncio

import pytest

from app.modules.exceptions.models import ExceptionSeverity, ExceptionType, ShipmentException
from app.modules.exceptions.rules import DuplicateActiveExceptionError
from app.modules.exceptions.schemas import ExceptionCreate
from app.modules.exceptions.service import ExceptionService
from app.modules.orders.models import Order
from app.modules.orders.service import OrderHasShipmentsError, OrderService
from app.modules.shipments.service import ShipmentService
from tests.db import factories as f
from tests.db.conftest import CommittedWorld, SessionFactory, cleanup


async def _assert_blocked(task: "asyncio.Task[object]") -> None:
    await asyncio.sleep(0.3)
    assert not task.done(), "the second transaction should be waiting for the first"


async def test_order_delete_loses_race_against_new_shipment(
    session_factory: SessionFactory, committed_world: CommittedWorld
) -> None:
    """The service checks "has shipments?" first; a shipment inserted in between must still be
    caught, by the foreign key, and reported as a conflict (not a 500)."""
    async with session_factory() as setup:
        bare_order = f.make_order()
        setup.add(bare_order)
        await setup.commit()

    try:
        async with session_factory() as writer, session_factory() as deleter:
            writer.add(f.make_shipment(bare_order, committed_world.warehouse))
            await writer.flush()  # inserted, not yet committed: invisible to the deleter

            deletion = asyncio.create_task(OrderService(deleter).delete(bare_order.id))
            await _assert_blocked(deletion)  # the DELETE waits for the writer's row lock
            await writer.commit()

            with pytest.raises(OrderHasShipmentsError):
                await deletion
        async with session_factory() as check:
            assert await check.get(Order, bare_order.id) is not None  # not deleted
    finally:
        await cleanup(session_factory, bare_order)


async def test_duplicate_active_exception_race_is_reported_as_conflict(
    session_factory: SessionFactory, committed_world: CommittedWorld
) -> None:
    """Two requests raise the same incident at once; the partial unique index decides."""
    shipment_id = committed_world.shipment.id

    async with session_factory() as first, session_factory() as second:
        first.add(
            ShipmentException(
                shipment_id=shipment_id,
                type=ExceptionType.DAMAGED,
                severity=ExceptionSeverity.LOW,
                description="first",
            )
        )
        await first.flush()  # not committed yet

        second_request = asyncio.create_task(
            ExceptionService(second).raise_new(
                shipment_id, ExceptionType.DAMAGED, ExceptionSeverity.LOW, "second"
            )
        )
        await _assert_blocked(second_request)  # waits on the unique index entry
        await first.commit()

        with pytest.raises(DuplicateActiveExceptionError):
            await second_request


async def test_manual_exception_waits_for_an_event_being_recorded(
    session_factory: SessionFactory, committed_world: CommittedWorld
) -> None:
    """An event handler (which locks the shipment) is about to raise a DELAYED exception.
    A manual DELAYED exception for the same shipment must wait and then be rejected cleanly;
    otherwise whichever commits second crashes on the unique index with a 500."""
    shipment_id = committed_world.shipment.id

    async with session_factory() as automatic, session_factory() as manual:
        await ShipmentService(automatic).lock(shipment_id)
        await ExceptionService(automatic).raise_or_escalate(
            shipment_id, ExceptionType.DELAYED, ExceptionSeverity.MEDIUM, "reported delay"
        )

        request = ExceptionCreate(
            type=ExceptionType.DELAYED, severity=ExceptionSeverity.HIGH, description="manual"
        )
        manual_request = asyncio.create_task(
            ShipmentService(manual).raise_exception(shipment_id, request)
        )
        await _assert_blocked(manual_request)
        await automatic.commit()  # must succeed: nothing else slipped in

        with pytest.raises(DuplicateActiveExceptionError):
            await manual_request
