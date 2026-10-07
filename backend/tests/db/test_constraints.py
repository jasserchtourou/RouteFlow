"""The database itself must reject invalid data, independent of any application code."""

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import delete, func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.drivers.models import Driver
from app.modules.exceptions.models import (
    ExceptionSeverity,
    ExceptionStatus,
    ExceptionType,
    ShipmentException,
)
from app.modules.inventory.models import InventoryItem
from app.modules.orders.models import Order
from app.modules.shipments.models import Shipment, ShipmentStatus
from app.modules.tracking.models import TrackingEvent, TrackingEventType
from app.modules.warehouses.models import Dock, Equipment
from tests.db import factories as f


async def _count(session: AsyncSession, model: type) -> int:
    return await session.scalar(select(func.count()).select_from(model)) or 0


async def test_ids_and_timestamps_are_generated(session: AsyncSession) -> None:
    order = f.make_order()
    session.add(order)
    await session.flush()

    assert isinstance(order.id, uuid.UUID)
    assert order.created_at is not None
    assert order.updated_at is not None
    assert order.status.value == "PENDING"  # default applied


async def test_order_number_must_be_unique(session: AsyncSession) -> None:
    session.add_all([f.make_order(order_number="ORD-DUP"), f.make_order(order_number="ORD-DUP")])

    with pytest.raises(IntegrityError, match="uq_orders_order_number"):
        await session.flush()


async def test_inventory_reserved_cannot_exceed_quantity(session: AsyncSession) -> None:
    warehouse = f.make_warehouse()
    session.add(warehouse)
    await session.flush()
    session.add(f.make_inventory_item(warehouse, quantity=5, reserved_quantity=6))

    with pytest.raises(IntegrityError, match="reserved_within_quantity"):
        await session.flush()


async def test_inventory_sku_unique_per_warehouse(session: AsyncSession) -> None:
    warehouse = f.make_warehouse()
    session.add(warehouse)
    await session.flush()
    session.add_all(
        [
            f.make_inventory_item(warehouse, sku="SKU-X"),
            f.make_inventory_item(warehouse, sku="SKU-X"),
        ]
    )

    with pytest.raises(IntegrityError, match="uq_inventory_items_warehouse_sku"):
        await session.flush()


async def test_same_sku_allowed_in_different_warehouses(session: AsyncSession) -> None:
    first, second = f.make_warehouse(), f.make_warehouse()
    session.add_all([first, second])
    await session.flush()
    session.add_all(
        [f.make_inventory_item(first, sku="SKU-X"), f.make_inventory_item(second, sku="SKU-X")]
    )

    await session.flush()  # no error


async def test_warehouse_utilization_cannot_exceed_capacity(session: AsyncSession) -> None:
    session.add(f.make_warehouse(capacity=100, current_utilization=101))

    with pytest.raises(IntegrityError, match="utilization_within_capacity"):
        await session.flush()


@pytest.mark.parametrize("fuel", [-1.0, 100.5])
async def test_vehicle_fuel_level_must_be_a_percentage(session: AsyncSession, fuel: float) -> None:
    session.add(f.make_vehicle(fuel_level=fuel))

    with pytest.raises(IntegrityError, match="fuel_level_percent"):
        await session.flush()


async def test_invalid_enum_value_is_rejected_by_database(session: AsyncSession) -> None:
    """Bypass the ORM: only the CHECK constraint stands between us and bad data."""
    with pytest.raises(IntegrityError, match="ck_orders_status_valid"):
        await session.execute(
            text(
                "INSERT INTO orders (order_number, customer_name, origin, destination, status,"
                " priority, promised_delivery_at) VALUES ('ORD-RAW', 'x', 'a', 'b', 'TELEPORTED',"
                " 'LOW', now())"
            )
        )


async def test_actual_delivery_requires_delivered_status(session: AsyncSession) -> None:
    order, warehouse = f.make_order(), f.make_warehouse()
    session.add_all([order, warehouse])
    await session.flush()
    session.add(
        f.make_shipment(
            order, warehouse, status=ShipmentStatus.IN_TRANSIT, actual_delivery=datetime.now(UTC)
        )
    )

    with pytest.raises(IntegrityError, match="actual_delivery_only_when_delivered"):
        await session.flush()


async def test_shipment_requires_existing_order(session: AsyncSession) -> None:
    warehouse = f.make_warehouse()
    session.add(warehouse)
    await session.flush()
    ghost_order = Order(id=uuid.uuid4())  # never inserted
    session.add(f.make_shipment(ghost_order, warehouse))

    with pytest.raises(IntegrityError, match="fk_shipments_order_id_orders"):
        await session.flush()


@pytest.mark.parametrize(
    ("status", "resolved_at", "valid"),
    [
        (ExceptionStatus.OPEN, None, True),
        (ExceptionStatus.RESOLVED, datetime(2026, 1, 1, tzinfo=UTC), True),
        (ExceptionStatus.RESOLVED, None, False),
        (ExceptionStatus.OPEN, datetime(2026, 1, 1, tzinfo=UTC), False),
    ],
)
async def test_exception_resolved_at_matches_status(
    session: AsyncSession, status: ExceptionStatus, resolved_at: datetime | None, valid: bool
) -> None:
    order, warehouse = f.make_order(), f.make_warehouse()
    session.add_all([order, warehouse])
    await session.flush()
    shipment = f.make_shipment(order, warehouse)
    session.add(shipment)
    await session.flush()
    session.add(
        ShipmentException(
            shipment_id=shipment.id,
            type=ExceptionType.DELAYED,
            severity=ExceptionSeverity.LOW,
            description="x",
            status=status,
            resolved_at=resolved_at,
            resolution_note="done" if status == ExceptionStatus.RESOLVED else None,
        )
    )

    if valid:
        await session.flush()
    else:
        with pytest.raises(IntegrityError, match="resolved_at_matches_status"):
            await session.flush()


async def test_deleting_shipment_cascades_to_events_and_exceptions(session: AsyncSession) -> None:
    order, warehouse = f.make_order(), f.make_warehouse()
    session.add_all([order, warehouse])
    await session.flush()
    shipment = f.make_shipment(order, warehouse)
    session.add(shipment)
    await session.flush()
    session.add_all(
        [
            TrackingEvent(
                shipment_id=shipment.id,
                event_type=TrackingEventType.CREATED,
                location="Hannover",
                occurred_at=datetime.now(UTC),
            ),
            ShipmentException(
                shipment_id=shipment.id,
                type=ExceptionType.DAMAGED,
                severity=ExceptionSeverity.LOW,
                description="x",
            ),
        ]
    )
    await session.flush()

    await session.execute(delete(Shipment).where(Shipment.id == shipment.id))

    assert await _count(session, TrackingEvent) == 0
    assert await _count(session, ShipmentException) == 0


async def test_order_with_shipments_cannot_be_deleted(session: AsyncSession) -> None:
    order, warehouse = f.make_order(), f.make_warehouse()
    session.add_all([order, warehouse])
    await session.flush()
    session.add(f.make_shipment(order, warehouse))
    await session.flush()

    with pytest.raises(IntegrityError, match="fk_shipments_order_id_orders"):
        await session.execute(delete(Order).where(Order.id == order.id))


async def test_deleting_warehouse_removes_its_inventory(session: AsyncSession) -> None:
    warehouse = f.make_warehouse()
    session.add(warehouse)
    await session.flush()
    session.add(f.make_inventory_item(warehouse))
    await session.flush()

    await session.execute(text("DELETE FROM warehouses WHERE id = :id"), {"id": warehouse.id})

    assert await _count(session, InventoryItem) == 0


async def test_deleting_vehicle_keeps_shipment_and_clears_reference(session: AsyncSession) -> None:
    order, warehouse, vehicle = f.make_order(), f.make_warehouse(), f.make_vehicle()
    session.add_all([order, warehouse, vehicle])
    await session.flush()
    shipment = f.make_shipment(order, warehouse, vehicle_id=vehicle.id)
    session.add(shipment)
    await session.flush()

    await session.execute(text("DELETE FROM vehicles WHERE id = :id"), {"id": vehicle.id})
    await session.refresh(shipment)

    assert shipment.vehicle_id is None


async def test_driver_can_drive_only_one_vehicle(session: AsyncSession) -> None:
    driver = Driver(full_name="A B", license_number="DE-1")
    session.add(driver)
    await session.flush()
    session.add_all([f.make_vehicle(driver_id=driver.id), f.make_vehicle(driver_id=driver.id)])

    with pytest.raises(IntegrityError, match="uq_vehicles_driver_id"):
        await session.flush()


async def test_dock_code_and_position_unique_per_warehouse(session: AsyncSession) -> None:
    warehouse = f.make_warehouse()
    session.add(warehouse)
    await session.flush()
    session.add_all([f.make_dock(warehouse, code="In 1"), f.make_dock(warehouse, code="In 1")])

    with pytest.raises(IntegrityError, match="uq_docks_warehouse_code"):
        await session.flush()


async def test_dock_position_unique_per_warehouse(session: AsyncSession) -> None:
    warehouse = f.make_warehouse()
    session.add(warehouse)
    await session.flush()
    session.add_all([f.make_dock(warehouse, position=1), f.make_dock(warehouse, position=1)])

    with pytest.raises(IntegrityError, match="uq_docks_warehouse_position"):
        await session.flush()


@pytest.mark.parametrize("battery", [-0.1, 100.1])
async def test_equipment_battery_is_a_percentage(session: AsyncSession, battery: float) -> None:
    warehouse = f.make_warehouse()
    session.add(warehouse)
    await session.flush()
    session.add(f.make_equipment(warehouse, battery_level=battery))

    with pytest.raises(IntegrityError, match="battery_level_percent"):
        await session.flush()


async def test_deleting_warehouse_removes_docks_and_equipment(session: AsyncSession) -> None:
    warehouse = f.make_warehouse()
    session.add(warehouse)
    await session.flush()
    session.add_all([f.make_dock(warehouse), f.make_equipment(warehouse)])
    await session.flush()

    await session.execute(text("DELETE FROM warehouses WHERE id = :id"), {"id": warehouse.id})

    assert await _count(session, Dock) == 0
    assert await _count(session, Equipment) == 0


async def test_resolved_exception_requires_resolution_note(session: AsyncSession) -> None:
    order, warehouse = f.make_order(), f.make_warehouse()
    session.add_all([order, warehouse])
    await session.flush()
    shipment = f.make_shipment(order, warehouse)
    session.add(shipment)
    await session.flush()
    session.add(
        ShipmentException(
            shipment_id=shipment.id,
            type=ExceptionType.DAMAGED,
            severity=ExceptionSeverity.LOW,
            description="x",
            status=ExceptionStatus.RESOLVED,
            resolved_at=datetime.now(UTC),
        )
    )

    with pytest.raises(IntegrityError, match="resolution_note_when_resolved"):
        await session.flush()
