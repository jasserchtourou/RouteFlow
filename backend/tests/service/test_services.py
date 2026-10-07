"""Service-layer tests: call the use cases directly, without HTTP.

API tests prove the endpoints work end to end; these pin down behaviour that is awkward to see
through HTTP - transaction ownership, no-op paths and error types.
"""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.modules.exceptions.models import (
    ExceptionSeverity,
    ExceptionStatus,
    ExceptionType,
    ShipmentException,
)
from app.modules.exceptions.schemas import ExceptionUpdate
from app.modules.exceptions.service import ExceptionClosedError, ExceptionService
from app.modules.orders.models import Order, OrderStatus
from app.modules.orders.rules import OrderCancelledError
from app.modules.orders.service import OrderService
from app.modules.shipments.models import Shipment, ShipmentStatus
from app.modules.shipments.service import ShipmentService
from app.modules.vehicles.service import VehicleService
from tests.db import factories as f


async def _shipment_with_order(
    session: AsyncSession, **order_overrides: object
) -> tuple[Order, Shipment]:
    order, warehouse = f.make_order(**order_overrides), f.make_warehouse()
    session.add_all([order, warehouse])
    await session.flush()
    shipment = f.make_shipment(order, warehouse)
    session.add(shipment)
    await session.flush()
    return order, shipment


async def _count_exceptions(session: AsyncSession) -> int:
    return await session.scalar(select(func.count()).select_from(ShipmentException)) or 0


# --- OrderService ---------------------------------------------------------------------------


async def test_order_ignores_shipment_statuses_without_order_meaning(
    session: AsyncSession,
) -> None:
    order, _ = await _shipment_with_order(session, status=OrderStatus.CONFIRMED)

    await OrderService(session).follow_shipment(order.id, ShipmentStatus.CREATED)

    assert order.status == OrderStatus.CONFIRMED


async def test_order_becomes_shipped_when_its_shipment_is_loaded(session: AsyncSession) -> None:
    order, _ = await _shipment_with_order(session, status=OrderStatus.CONFIRMED)

    await OrderService(session).follow_shipment(order.id, ShipmentStatus.LOADED)

    assert order.status == OrderStatus.SHIPPED


async def test_order_never_moves_backwards_when_events_arrive_late(session: AsyncSession) -> None:
    order, _ = await _shipment_with_order(session, status=OrderStatus.SHIPPED)

    await OrderService(session).follow_shipment(order.id, ShipmentStatus.PICKED)

    assert order.status == OrderStatus.SHIPPED


async def test_cancelled_order_cannot_follow_a_shipment(session: AsyncSession) -> None:
    order, _ = await _shipment_with_order(session, status=OrderStatus.CANCELLED)

    with pytest.raises(OrderCancelledError):
        await OrderService(session).ensure_can_follow_shipment(order.id)


async def test_order_service_raises_not_found_for_unknown_ids(session: AsyncSession) -> None:
    service = OrderService(session)

    with pytest.raises(NotFoundError):
        await service.get(uuid.uuid4())
    with pytest.raises(NotFoundError):
        await service.get_by_number("ORD-0")


# --- ExceptionService -----------------------------------------------------------------------


async def test_raise_or_escalate_leaves_committing_to_the_caller(session: AsyncSession) -> None:
    """Automatic detection runs inside someone else's transaction: it must not commit."""
    _, shipment = await _shipment_with_order(session)
    service = ExceptionService(session)

    await service.raise_or_escalate(
        shipment.id, ExceptionType.DELAYED, ExceptionSeverity.MEDIUM, "late"
    )
    await session.rollback()  # the caller decides to abort

    assert await _count_exceptions(session) == 0


async def test_escalation_updates_the_active_exception_instead_of_adding_one(
    session: AsyncSession,
) -> None:
    _, shipment = await _shipment_with_order(session)
    service = ExceptionService(session)

    first = await service.raise_or_escalate(
        shipment.id, ExceptionType.DELAYED, ExceptionSeverity.MEDIUM, "30 min"
    )
    await session.flush()
    second = await service.raise_or_escalate(
        shipment.id, ExceptionType.DELAYED, ExceptionSeverity.LOW, "60 min"
    )
    await session.flush()

    assert second is first
    assert second.severity == ExceptionSeverity.MEDIUM  # a lower severity never downgrades
    assert second.description == "60 min"  # but the description is kept current
    assert await _count_exceptions(session) == 1


async def test_a_new_exception_is_raised_after_the_old_one_was_resolved(
    session: AsyncSession,
) -> None:
    _, shipment = await _shipment_with_order(session)
    service = ExceptionService(session)
    old = await service.raise_new(shipment.id, ExceptionType.DAMAGED, ExceptionSeverity.LOW, "x")
    await service.update(
        old.id, ExceptionUpdate(status=ExceptionStatus.RESOLVED, resolution_note="repacked")
    )

    new = await service.raise_or_escalate(
        shipment.id, ExceptionType.DAMAGED, ExceptionSeverity.HIGH, "again"
    )

    assert new.id != old.id
    assert new.status == ExceptionStatus.OPEN


async def test_update_exception_changes_only_what_was_sent(session: AsyncSession) -> None:
    _, shipment = await _shipment_with_order(session)
    service = ExceptionService(session)
    created = await service.raise_new(
        shipment.id, ExceptionType.MISSING_DOCUMENT, ExceptionSeverity.LOW, "no CMR"
    )

    escalated = await service.update(created.id, ExceptionUpdate(severity=ExceptionSeverity.HIGH))
    noted = await service.update(created.id, ExceptionUpdate(resolution_note="called carrier"))
    same_status = await service.update(created.id, ExceptionUpdate(status=ExceptionStatus.OPEN))

    assert (escalated.severity, escalated.status) == (ExceptionSeverity.HIGH, ExceptionStatus.OPEN)
    assert noted.resolution_note == "called carrier"
    assert noted.status == ExceptionStatus.OPEN
    assert same_status.status == ExceptionStatus.OPEN  # re-sending the same status is a no-op


async def test_resolving_uses_a_note_saved_earlier(session: AsyncSession) -> None:
    _, shipment = await _shipment_with_order(session)
    service = ExceptionService(session)
    created = await service.raise_new(
        shipment.id, ExceptionType.DAMAGED, ExceptionSeverity.LOW, "dent"
    )
    await service.update(created.id, ExceptionUpdate(resolution_note="claim filed"))

    resolved = await service.update(created.id, ExceptionUpdate(status=ExceptionStatus.RESOLVED))

    assert resolved.status == ExceptionStatus.RESOLVED
    assert resolved.resolution_note == "claim filed"
    assert resolved.resolved_at is not None


async def test_exception_service_error_types(session: AsyncSession) -> None:
    _, shipment = await _shipment_with_order(session)
    service = ExceptionService(session)
    created = await service.raise_new(
        shipment.id, ExceptionType.DAMAGED, ExceptionSeverity.LOW, "dent"
    )
    await service.update(
        created.id, ExceptionUpdate(status=ExceptionStatus.RESOLVED, resolution_note="done")
    )

    with pytest.raises(NotFoundError):
        await service.get(uuid.uuid4())
    with pytest.raises(NotFoundError):
        await service.update(uuid.uuid4(), ExceptionUpdate(severity=ExceptionSeverity.LOW))
    with pytest.raises(ExceptionClosedError):
        await service.update(created.id, ExceptionUpdate(severity=ExceptionSeverity.HIGH))
    assert await service.read_many([]) == []


# --- Shipment / vehicle services ------------------------------------------------------------


async def test_shipment_service_not_found_paths(session: AsyncSession) -> None:
    service = ShipmentService(session)
    missing = uuid.uuid4()

    for call in (service.get, service.lock, service.read, service.detail):
        with pytest.raises(NotFoundError):
            await call(missing)
    with pytest.raises(NotFoundError):
        await service.detail_by_number("SHP-0")


async def test_vehicle_service_not_found_paths(session: AsyncSession) -> None:
    service = VehicleService(session)

    with pytest.raises(NotFoundError):
        await service.get(uuid.uuid4())
    with pytest.raises(NotFoundError):
        await service.get_by_registration("XX-YY 1")


async def test_shipment_detail_reports_delay_from_one_reference_time(
    session: AsyncSession,
) -> None:
    order, warehouse = f.make_order(), f.make_warehouse()
    session.add_all([order, warehouse])
    await session.flush()
    shipment = f.make_shipment(
        order,
        warehouse,
        status=ShipmentStatus.IN_TRANSIT,
        estimated_delivery=datetime.now(UTC) - timedelta(minutes=45),
    )
    session.add(shipment)
    await session.flush()

    detail = await ShipmentService(session).detail(shipment.id)

    assert detail.is_delayed is True
    assert 44 <= detail.delay_minutes <= 46
