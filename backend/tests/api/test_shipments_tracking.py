"""Shipments, tracking events and exceptions against real PostgreSQL."""

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.exceptions.models import (
    ExceptionSeverity,
    ExceptionStatus,
    ExceptionType,
    ShipmentException,
)
from app.modules.orders.models import Order, OrderStatus
from app.modules.shipments.models import Shipment, ShipmentStatus, TemperatureStatus
from app.modules.tracking.models import TrackingEvent, TrackingEventType
from app.modules.warehouses.models import Warehouse
from tests.db import factories as f

API = "/api/v1"


@dataclass
class World:
    order: Order
    warehouse: Warehouse
    shipment: Shipment

    @property
    def events_url(self) -> str:
        return f"{API}/shipments/{self.shipment.id}/events"


async def _world(
    session: AsyncSession,
    *,
    status: ShipmentStatus = ShipmentStatus.CREATED,
    order_status: OrderStatus = OrderStatus.CONFIRMED,
    cold: bool = False,
    eta: datetime | None = None,
    created_hours_ago: float = 6,
    **shipment: Any,
) -> World:
    order = f.make_order(status=order_status)
    warehouse = f.make_warehouse(code=f"WH-{uuid.uuid4().hex[:6].upper()}")
    session.add_all([order, warehouse])
    await session.flush()
    created = datetime.now(UTC) - timedelta(hours=created_hours_ago)
    ship = f.make_shipment(
        order,
        warehouse,
        status=status,
        temperature_status=TemperatureStatus.NORMAL if cold else TemperatureStatus.NOT_APPLICABLE,
        estimated_delivery=eta or datetime.now(UTC) + timedelta(hours=4),
        created_at=created,
        **shipment,
    )
    session.add(ship)
    await session.flush()
    session.add(
        TrackingEvent(
            shipment_id=ship.id,
            event_type=TrackingEventType.CREATED,
            location=warehouse.name,
            occurred_at=created,
        )
    )
    await session.flush()
    return World(order, warehouse, ship)


def _event(event_type: str, **extra: Any) -> dict[str, Any]:
    return {"event_type": event_type, "location": "Hannover depot", **extra}


async def _exceptions_of(session: AsyncSession, shipment: Shipment) -> list[ShipmentException]:
    result = await session.scalars(
        select(ShipmentException).where(ShipmentException.shipment_id == shipment.id)
    )
    return list(result.all())


# --- shipments ------------------------------------------------------------------------------


async def test_list_shipments_with_context(db_client: AsyncClient, session: AsyncSession) -> None:
    world = await _world(session)

    item = (await db_client.get(f"{API}/shipments")).json()["items"][0]

    assert item["shipment_number"] == world.shipment.shipment_number
    assert item["order_number"] == world.order.order_number
    assert item["warehouse_code"] == world.warehouse.code
    assert item["route_number"] is None
    assert item["vehicle_registration"] is None
    assert item["is_delayed"] is False
    assert item["active_exception_count"] == 0


async def test_delayed_filter_and_delay_minutes(
    db_client: AsyncClient, session: AsyncSession
) -> None:
    late = await _world(session, status=ShipmentStatus.IN_TRANSIT,
                        eta=datetime.now(UTC) - timedelta(minutes=95))  # fmt: skip
    await _world(session, status=ShipmentStatus.IN_TRANSIT)  # on time
    await _world(session, status=ShipmentStatus.DELIVERED, actual_delivery=datetime.now(UTC),
                 eta=datetime.now(UTC) - timedelta(hours=1))  # fmt: skip

    delayed = (await db_client.get(f"{API}/shipments", params={"delayed": "true"})).json()
    on_time = (await db_client.get(f"{API}/shipments", params={"delayed": "false"})).json()

    assert [s["shipment_number"] for s in delayed["items"]] == [late.shipment.shipment_number]
    assert delayed["items"][0]["delay_minutes"] in (94, 95, 96)
    assert on_time["total"] == 2


async def test_shipment_filters(db_client: AsyncClient, session: AsyncSession) -> None:
    cold = await _world(session, cold=True, destination="Berlin")
    ambient = await _world(session, status=ShipmentStatus.PICKED)
    session.add(
        ShipmentException(
            shipment_id=ambient.shipment.id,
            type=ExceptionType.DAMAGED,
            severity=ExceptionSeverity.LOW,
            description="dented",
        )
    )
    await session.flush()

    async def numbers(**params: Any) -> set[str]:
        body = (await db_client.get(f"{API}/shipments", params=params)).json()
        return {s["shipment_number"] for s in body["items"]}

    assert await numbers(temperature_status="NORMAL") == {cold.shipment.shipment_number}
    assert await numbers(destination="berlin") == {cold.shipment.shipment_number}
    assert await numbers(status="PICKED") == {ambient.shipment.shipment_number}
    assert await numbers(has_active_exception="true") == {ambient.shipment.shipment_number}
    assert await numbers(warehouse_code=cold.warehouse.code.lower()) == {
        cold.shipment.shipment_number
    }
    assert await numbers(search=ambient.order.order_number) == {ambient.shipment.shipment_number}


async def test_sort_by_eta_puts_most_overdue_first(
    db_client: AsyncClient, session: AsyncSession
) -> None:
    now = datetime.now(UTC)
    worlds = [await _world(session, eta=now + timedelta(hours=h)) for h in (3, -2, 1)]

    body = (await db_client.get(f"{API}/shipments", params={"sort": "estimated_delivery"})).json()

    expected = [worlds[1], worlds[2], worlds[0]]
    assert [s["shipment_number"] for s in body["items"]] == [
        w.shipment.shipment_number for w in expected
    ]


async def test_shipment_detail_by_id_and_number(
    db_client: AsyncClient, session: AsyncSession
) -> None:
    world = await _world(session)

    by_id = (await db_client.get(f"{API}/shipments/{world.shipment.id}")).json()
    number = world.shipment.shipment_number.lower()  # case-insensitive lookup
    by_number = (await db_client.get(f"{API}/shipments/by-number/{number}")).json()

    assert by_id == by_number
    assert by_id["latest_event"]["event_type"] == "CREATED"
    assert by_id["active_exceptions"] == []


@pytest.mark.parametrize(
    "path", ["/shipments/{id}", "/shipments/{id}/tracking", "/exceptions/{id}"]
)
async def test_unknown_ids_return_404(db_client: AsyncClient, path: str) -> None:
    assert (await db_client.get(API + path.format(id=uuid.uuid4()))).status_code == 404


async def test_post_event_to_unknown_shipment_returns_404(db_client: AsyncClient) -> None:
    response = await db_client.post(f"{API}/shipments/{uuid.uuid4()}/events", json=_event("PICKED"))

    assert response.status_code == 404


# --- lifecycle via tracking events ----------------------------------------------------------


async def test_full_lifecycle_moves_shipment_and_order(
    db_client: AsyncClient, session: AsyncSession
) -> None:
    world = await _world(session, order_status=OrderStatus.PENDING)
    steps = [
        ("PICKED", "PICKED", "PROCESSING"),
        ("PACKED", "PACKED", "PROCESSING"),
        ("LOADED", "LOADED", "SHIPPED"),
        ("DEPARTED", "IN_TRANSIT", "SHIPPED"),
        ("CHECKPOINT", "IN_TRANSIT", "SHIPPED"),  # informational: no status change
        ("OUT_FOR_DELIVERY", "OUT_FOR_DELIVERY", "SHIPPED"),
        ("DELIVERED", "DELIVERED", "DELIVERED"),
    ]

    for event_type, shipment_status, order_status in steps:
        response = await db_client.post(world.events_url, json=_event(event_type))
        assert response.status_code == 201, response.text
        assert response.json()["shipment"]["status"] == shipment_status
        order = (await db_client.get(f"{API}/orders/{world.order.id}")).json()
        assert order["status"] == order_status, event_type

    shipment = (await db_client.get(f"{API}/shipments/{world.shipment.id}")).json()
    assert shipment["actual_delivery"] is not None
    history = (await db_client.get(f"{API}/shipments/{world.shipment.id}/tracking")).json()
    assert [e["event_type"] for e in history] == ["CREATED"] + [s[0] for s in steps]


async def test_skipping_a_step_is_rejected_and_nothing_is_stored(
    db_client: AsyncClient, session: AsyncSession
) -> None:
    world = await _world(session)

    response = await db_client.post(world.events_url, json=_event("LOADED"))

    assert response.status_code == 409
    error = response.json()["error"]
    assert error["code"] == "invalid_status_transition"
    assert error["details"] == {"current": "CREATED", "requested": "LOADED", "allowed": "PICKED"}
    history = (await db_client.get(f"{API}/shipments/{world.shipment.id}/tracking")).json()
    assert len(history) == 1  # only CREATED


async def test_delivered_shipment_accepts_no_more_events(
    db_client: AsyncClient, session: AsyncSession
) -> None:
    world = await _world(
        session, status=ShipmentStatus.DELIVERED, actual_delivery=datetime.now(UTC)
    )

    response = await db_client.post(world.events_url, json=_event("CHECKPOINT"))

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "shipment_closed"


async def test_cancelled_order_blocks_shipment_progress(
    db_client: AsyncClient, session: AsyncSession
) -> None:
    world = await _world(session, order_status=OrderStatus.CANCELLED)

    response = await db_client.post(world.events_url, json=_event("PICKED"))

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "order_cancelled"


async def test_order_delivered_only_when_all_shipments_are(
    db_client: AsyncClient, session: AsyncSession
) -> None:
    world = await _world(session, status=ShipmentStatus.OUT_FOR_DELIVERY,
                         order_status=OrderStatus.SHIPPED)  # fmt: skip
    session.add(f.make_shipment(world.order, world.warehouse, status=ShipmentStatus.IN_TRANSIT))
    await session.flush()

    await db_client.post(world.events_url, json=_event("DELIVERED"))

    order = (await db_client.get(f"{API}/orders/{world.order.id}")).json()
    assert order["status"] == "SHIPPED"  # the second shipment is still on its way


async def test_status_change_cannot_be_backdated(
    db_client: AsyncClient, session: AsyncSession
) -> None:
    world = await _world(session, created_hours_ago=10)
    await db_client.post(world.events_url, json=_event("PICKED"))
    earlier = (datetime.now(UTC) - timedelta(hours=1)).isoformat()

    backdated = await db_client.post(world.events_url, json=_event("PACKED", occurred_at=earlier))
    late_scan = await db_client.post(
        world.events_url, json=_event("CHECKPOINT", occurred_at=earlier)
    )

    assert backdated.status_code == 422
    assert backdated.json()["error"]["code"] == "event_out_of_order"
    assert late_scan.status_code == 201  # late-synced informational scans are accepted


@pytest.mark.parametrize(
    ("body", "message"),
    [
        (_event("CREATED"), "created by the system"),
        (_event("TELEPORTED"), "Input should be"),
        (_event("TEMPERATURE_ALERT"), "temperature_c"),
        (_event("TEMPERATURE_ALERT", details={"temperature_c": "hot"}), "temperature_c"),
        (_event("DELAY_REPORTED", details={"delay_minutes": 0}), "delay_minutes"),
        (_event("DELAY_REPORTED", details={"delay_minutes": True}), "delay_minutes"),
        (_event("PICKED", occurred_at="2099-01-01T00:00:00Z"), "future"),
        (_event("PICKED", occurred_at="2026-10-07T10:00:00"), "timezone"),
        ({"event_type": "PICKED"}, "location"),
    ],
)
async def test_invalid_event_payloads_return_422(
    db_client: AsyncClient, session: AsyncSession, body: dict[str, Any], message: str
) -> None:
    world = await _world(session)

    response = await db_client.post(world.events_url, json=body)

    assert response.status_code == 422
    assert message in response.text


# --- events that raise exceptions -----------------------------------------------------------


async def test_temperature_alert_raises_critical_exception(
    db_client: AsyncClient, session: AsyncSession
) -> None:
    world = await _world(session, status=ShipmentStatus.IN_TRANSIT, cold=True)

    response = await db_client.post(
        world.events_url, json=_event("TEMPERATURE_ALERT", details={"temperature_c": 11.5})
    )

    body = response.json()
    assert response.status_code == 201
    assert body["shipment"]["temperature_status"] == "DEVIATION"
    assert body["shipment"]["status"] == "IN_TRANSIT"  # informational, no status change
    [raised] = body["exceptions"]
    assert raised["type"] == "TEMPERATURE_DEVIATION"
    assert raised["severity"] == "CRITICAL"  # 3.5 °C above the band
    assert "11.5 °C" in raised["description"]


async def test_repeated_alerts_escalate_instead_of_duplicating(
    db_client: AsyncClient, session: AsyncSession
) -> None:
    world = await _world(session, status=ShipmentStatus.IN_TRANSIT, cold=True)

    first = await db_client.post(
        world.events_url, json=_event("TEMPERATURE_ALERT", details={"temperature_c": 9.0})
    )
    second = await db_client.post(
        world.events_url, json=_event("TEMPERATURE_ALERT", details={"temperature_c": 12.0})
    )
    third = await db_client.post(
        world.events_url, json=_event("TEMPERATURE_ALERT", details={"temperature_c": 8.5})
    )

    assert first.json()["exceptions"][0]["severity"] == "HIGH"
    assert second.json()["exceptions"][0]["severity"] == "CRITICAL"
    assert third.json()["exceptions"][0]["severity"] == "CRITICAL"  # never downgraded
    assert len(await _exceptions_of(session, world.shipment)) == 1


async def test_in_band_reading_raises_nothing(
    db_client: AsyncClient, session: AsyncSession
) -> None:
    world = await _world(session, status=ShipmentStatus.IN_TRANSIT, cold=True)

    response = await db_client.post(
        world.events_url, json=_event("TEMPERATURE_ALERT", details={"temperature_c": 5.0})
    )

    assert response.json()["exceptions"] == []
    assert response.json()["shipment"]["temperature_status"] == "NORMAL"


async def test_temperature_alert_on_ambient_goods_is_rejected(
    db_client: AsyncClient, session: AsyncSession
) -> None:
    world = await _world(session, status=ShipmentStatus.IN_TRANSIT)

    response = await db_client.post(
        world.events_url, json=_event("TEMPERATURE_ALERT", details={"temperature_c": 12.0})
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "not_temperature_controlled"


async def test_delay_report_shifts_eta_and_raises_exception(
    db_client: AsyncClient, session: AsyncSession
) -> None:
    eta = datetime.now(UTC) + timedelta(hours=1)
    world = await _world(session, status=ShipmentStatus.IN_TRANSIT, eta=eta)

    response = await db_client.post(
        world.events_url,
        json=_event("DELAY_REPORTED", details={"delay_minutes": 150, "reason": "A2 closure"}),
    )

    body = response.json()
    new_eta = datetime.fromisoformat(body["shipment"]["estimated_delivery"])
    assert new_eta == eta + timedelta(minutes=150)
    [raised] = body["exceptions"]
    assert (raised["type"], raised["severity"]) == ("DELAYED", "HIGH")
    assert "A2 closure" in raised["description"]
    assert body["shipment"]["active_exception_count"] == 1


# --- exceptions -----------------------------------------------------------------------------


async def test_manually_raise_exception_and_reject_duplicates(
    db_client: AsyncClient, session: AsyncSession
) -> None:
    world = await _world(session)
    url = f"{API}/shipments/{world.shipment.id}/exceptions"
    body = {"type": "DAMAGED", "severity": "MEDIUM", "description": "Pallet wrap torn"}

    created = await db_client.post(url, json=body)
    duplicate = await db_client.post(url, json=body)

    assert created.status_code == 201
    assert created.json()["status"] == "OPEN"
    assert created.json()["shipment_number"] == world.shipment.shipment_number
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "duplicate_active_exception"


async def test_exception_workflow_to_resolution(
    db_client: AsyncClient, session: AsyncSession
) -> None:
    world = await _world(session)
    created = await db_client.post(
        f"{API}/shipments/{world.shipment.id}/exceptions",
        json={"type": "MISSING_DOCUMENT", "severity": "LOW", "description": "No CMR"},
    )
    url = f"{API}/exceptions/{created.json()['id']}"

    investigating = await db_client.patch(url, json={"status": "INVESTIGATING"})
    no_note = await db_client.patch(url, json={"status": "RESOLVED"})
    resolved = await db_client.patch(
        url, json={"status": "RESOLVED", "resolution_note": "CMR re-issued by carrier"}
    )
    after = await db_client.patch(url, json={"severity": "HIGH"})

    assert investigating.json()["status"] == "INVESTIGATING"
    assert no_note.status_code == 422
    assert resolved.json()["status"] == "RESOLVED"
    assert resolved.json()["resolved_at"] is not None
    assert after.status_code == 409
    assert after.json()["error"]["code"] == "exception_closed"


async def test_resolved_exception_allows_a_new_one_of_the_same_type(
    db_client: AsyncClient, session: AsyncSession
) -> None:
    world = await _world(session)
    url = f"{API}/shipments/{world.shipment.id}/exceptions"
    body = {"type": "DAMAGED", "severity": "LOW", "description": "x"}
    first = (await db_client.post(url, json=body)).json()
    await db_client.patch(
        f"{API}/exceptions/{first['id']}",
        json={"status": "RESOLVED", "resolution_note": "repacked"},
    )

    again = await db_client.post(url, json=body)

    assert again.status_code == 201  # the partial unique index only covers active incidents


async def test_list_exceptions_filters_and_severity_order(
    db_client: AsyncClient, session: AsyncSession
) -> None:
    world = await _world(session)
    now = datetime.now(UTC)
    for kind, severity, status in [
        (ExceptionType.DAMAGED, ExceptionSeverity.LOW, ExceptionStatus.OPEN),
        (ExceptionType.DELAYED, ExceptionSeverity.CRITICAL, ExceptionStatus.INVESTIGATING),
        (ExceptionType.MISSING_DOCUMENT, ExceptionSeverity.HIGH, ExceptionStatus.RESOLVED),
    ]:
        session.add(
            ShipmentException(
                shipment_id=world.shipment.id,
                type=kind,
                severity=severity,
                status=status,
                description="x",
                resolved_at=now if status == ExceptionStatus.RESOLVED else None,
                resolution_note="done" if status == ExceptionStatus.RESOLVED else None,
            )
        )
    await session.flush()

    async def kinds(**params: Any) -> list[str]:
        body = (await db_client.get(f"{API}/exceptions", params=params)).json()
        return [e["type"] for e in body["items"]]

    assert await kinds() == ["DELAYED", "MISSING_DOCUMENT", "DAMAGED"]  # by severity
    assert await kinds(active="true") == ["DELAYED", "DAMAGED"]
    assert await kinds(active="false") == ["MISSING_DOCUMENT"]
    assert await kinds(severity="LOW") == ["DAMAGED"]
    assert await kinds(type="DELAYED", warehouse_code=world.warehouse.code) == ["DELAYED"]
    assert await kinds(shipment_number=world.shipment.shipment_number.lower()) == [
        "DELAYED",
        "MISSING_DOCUMENT",
        "DAMAGED",
    ]


async def test_shipment_detail_shows_active_exceptions(
    db_client: AsyncClient, session: AsyncSession
) -> None:
    world = await _world(session, status=ShipmentStatus.IN_TRANSIT, cold=True)
    await db_client.post(
        world.events_url, json=_event("TEMPERATURE_ALERT", details={"temperature_c": 10.0})
    )

    detail = (await db_client.get(f"{API}/shipments/{world.shipment.id}")).json()

    assert detail["latest_event"]["event_type"] == "TEMPERATURE_ALERT"
    assert [e["type"] for e in detail["active_exceptions"]] == ["TEMPERATURE_DEVIATION"]
    assert detail["active_exception_count"] == 1


async def test_partial_unique_index_enforced_by_database(session: AsyncSession) -> None:
    """Even code that bypasses the service cannot create two active incidents of one type."""
    from sqlalchemy.exc import IntegrityError

    world = await _world(session)
    for _ in range(2):
        session.add(
            ShipmentException(
                shipment_id=world.shipment.id,
                type=ExceptionType.DELAYED,
                severity=ExceptionSeverity.LOW,
                description="x",
            )
        )

    with pytest.raises(IntegrityError, match="uq_shipment_exceptions_active_type"):
        await session.flush()
    await session.rollback()
    assert await session.scalar(select(func.count()).select_from(ShipmentException)) == 0


# --- network-wide event feed -----------------------------------------------------------------


async def _add_event(
    session: AsyncSession,
    world: World,
    event_type: TrackingEventType,
    minutes_ago: float,
    location: str = "Hannover depot",
) -> None:
    session.add(
        TrackingEvent(
            shipment_id=world.shipment.id,
            event_type=event_type,
            location=location,
            occurred_at=datetime.now(UTC) - timedelta(minutes=minutes_ago),
        )
    )
    await session.flush()


async def test_event_feed_lists_events_of_all_shipments_newest_first(
    db_client: AsyncClient, session: AsyncSession
) -> None:
    first = await _world(session, origin="Hamburg", destination="Hannover")
    second = await _world(session, origin="Berlin", destination="Leipzig")
    await _add_event(session, first, TrackingEventType.PICKED, minutes_ago=30)
    await _add_event(session, second, TrackingEventType.DEPARTED, minutes_ago=5)

    body = (await db_client.get(f"{API}/events")).json()

    assert body["total"] == 4  # two CREATED events from the fixtures + the two above
    assert [e["event_type"] for e in body["items"][:2]] == ["DEPARTED", "PICKED"]
    top = body["items"][0]
    assert top["shipment_number"] == second.shipment.shipment_number
    assert (top["origin"], top["destination"]) == ("Berlin", "Leipzig")
    assert top["location"] == "Hannover depot"


async def test_event_feed_filters_by_type_text_and_time(
    db_client: AsyncClient, session: AsyncSession
) -> None:
    ham = await _world(session, origin="Hamburg", destination="Hannover")
    ber = await _world(session, origin="Berlin", destination="Leipzig")
    await _add_event(session, ham, TrackingEventType.CHECKPOINT, 90, location="Autobahn A7")
    await _add_event(session, ber, TrackingEventType.CHECKPOINT, 10, location="Autobahn A9")
    await _add_event(session, ber, TrackingEventType.DELAY_REPORTED, 3)

    def numbers(body: dict[str, Any]) -> set[str]:
        return {e["shipment_number"] for e in body["items"]}

    by_type = (await db_client.get(f"{API}/events", params={"event_type": ["CHECKPOINT"]})).json()
    assert by_type["total"] == 2

    by_location = (await db_client.get(f"{API}/events", params={"search": "a7"})).json()
    assert numbers(by_location) == {ham.shipment.shipment_number}

    by_city = (await db_client.get(f"{API}/events", params={"search": "leipzig"})).json()
    assert numbers(by_city) == {ber.shipment.shipment_number}

    since = (datetime.now(UTC) - timedelta(minutes=30)).isoformat()
    recent = (await db_client.get(f"{API}/events", params={"since": since})).json()
    # The fixtures' CREATED events are hours old, the A7 checkpoint is 90 minutes old.
    assert {e["event_type"] for e in recent["items"]} == {"CHECKPOINT", "DELAY_REPORTED"}
    assert all(e["location"] != "Autobahn A7" for e in recent["items"])


async def test_event_feed_paginates_and_rejects_unknown_parameters(
    db_client: AsyncClient, session: AsyncSession
) -> None:
    world = await _world(session)
    for minutes in range(1, 6):
        await _add_event(session, world, TrackingEventType.CHECKPOINT, minutes)

    page = (await db_client.get(f"{API}/events", params={"limit": 2, "offset": 2})).json()
    assert (page["total"], len(page["items"]), page["limit"], page["offset"]) == (6, 2, 2, 2)

    assert (await db_client.get(f"{API}/events", params={"colour": "red"})).status_code == 422
