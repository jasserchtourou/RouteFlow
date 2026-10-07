"""Cross-cutting validation (every list / id endpoint) plus the remaining edge cases."""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.drivers.models import Driver
from app.modules.exceptions.models import (
    ExceptionSeverity,
    ExceptionStatus,
    ExceptionType,
    ShipmentException,
)
from app.modules.shipments.models import Shipment, ShipmentStatus, TemperatureStatus
from tests.db import factories as f

API = "/api/v1"

LIST_ENDPOINTS = [
    "/orders",
    "/warehouses",
    "/inventory/low-stock",
    "/shipments",
    "/exceptions",
    "/routes",
    "/vehicles",
    "/drivers",
]
ID_ENDPOINTS = [
    "/orders/{}",
    "/warehouses/{}",
    "/warehouses/{}/inventory",
    "/warehouses/{}/docks",
    "/warehouses/{}/equipment",
    "/shipments/{}",
    "/shipments/{}/tracking",
    "/exceptions/{}",
    "/routes/{}",
    "/vehicles/{}",
    "/drivers/{}",
]


# --- every list endpoint ---------------------------------------------------------------------


@pytest.mark.parametrize("path", LIST_ENDPOINTS)
async def test_list_endpoints_have_consistent_defaults(db_client: AsyncClient, path: str) -> None:
    body = (await db_client.get(API + path)).json()

    assert set(body) == {"items", "total", "limit", "offset"}
    assert (body["limit"], body["offset"]) == (20, 0)


@pytest.mark.parametrize("path", LIST_ENDPOINTS)
@pytest.mark.parametrize(
    "params", [{"limit": 0}, {"limit": 101}, {"offset": -1}, {"limit": "many"}, {"no_such": 1}]
)
async def test_list_endpoints_reject_bad_paging_and_unknown_params(
    db_client: AsyncClient, path: str, params: dict[str, Any]
) -> None:
    response = await db_client.get(API + path, params=params)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


@pytest.mark.parametrize("path", LIST_ENDPOINTS)
async def test_list_endpoints_reject_unknown_sort_keys(db_client: AsyncClient, path: str) -> None:
    """Sorting is whitelisted: user input never becomes a column name."""
    response = await db_client.get(API + path, params={"sort": "id; DROP TABLE orders"})

    assert response.status_code == 422


# --- every id endpoint -----------------------------------------------------------------------


@pytest.mark.parametrize("template", ID_ENDPOINTS)
async def test_malformed_ids_return_422(db_client: AsyncClient, template: str) -> None:
    response = await db_client.get(API + template.format("not-a-uuid"))

    assert response.status_code == 422


@pytest.mark.parametrize("template", ID_ENDPOINTS)
async def test_unknown_ids_return_404_in_the_error_envelope(
    db_client: AsyncClient, template: str
) -> None:
    response = await db_client.get(API + template.format(uuid.uuid4()))

    assert response.status_code == 404
    error = response.json()["error"]
    assert error["code"] == "not_found"
    assert error["request_id"] == response.headers["X-Request-ID"]


# --- remaining filters and sort orders --------------------------------------------------------


async def test_orders_created_before_filter_and_update_in_the_past(
    db_client: AsyncClient, session: AsyncSession
) -> None:
    now = datetime.now(UTC)
    old, recent = f.make_order(created_at=now - timedelta(days=9)), f.make_order()
    session.add_all([old, recent])
    await session.flush()

    body = (
        await db_client.get(
            f"{API}/orders", params={"created_before": (now - timedelta(days=1)).isoformat()}
        )
    ).json()
    past_update = await db_client.patch(
        f"{API}/orders/{recent.id}",
        json={"promised_delivery_at": (now - timedelta(hours=1)).isoformat()},
    )

    assert [o["id"] for o in body["items"]] == [str(old.id)]
    assert past_update.status_code == 422
    assert "in the future" in past_update.text


async def _shipment(session: AsyncSession, **overrides: Any) -> Shipment:
    order, warehouse = f.make_order(), f.make_warehouse()
    session.add_all([order, warehouse])
    await session.flush()
    shipment = f.make_shipment(order, warehouse, **overrides)
    session.add(shipment)
    await session.flush()
    return shipment


async def test_shipment_filters_by_route_vehicle_and_eta(
    db_client: AsyncClient, session: AsyncSession
) -> None:
    route, vehicle = f.make_route(route_number="RTE-777"), f.make_vehicle(registration="H-ZZ 1")
    session.add_all([route, vehicle])
    await session.flush()
    now = datetime.now(UTC)
    target = await _shipment(
        session,
        route_id=route.id,
        vehicle_id=vehicle.id,
        status=ShipmentStatus.IN_TRANSIT,
        estimated_delivery=now + timedelta(hours=5),
    )
    await _shipment(session, estimated_delivery=now + timedelta(hours=30))

    async def numbers(**params: Any) -> set[str]:
        body = (await db_client.get(f"{API}/shipments", params=params)).json()
        return {s["shipment_number"] for s in body["items"]}

    expected = {target.shipment_number}
    assert await numbers(route_number="rte-777") == expected
    assert await numbers(vehicle_registration="h-zz 1") == expected
    assert await numbers(eta_before=(now + timedelta(hours=12)).isoformat()) == expected
    assert target.shipment_number not in await numbers(
        eta_after=(now + timedelta(hours=12)).isoformat()
    )
    inverted = await db_client.get(
        f"{API}/shipments",
        params={"eta_after": (now + timedelta(hours=2)).isoformat(), "eta_before": now.isoformat()},
    )
    assert inverted.status_code == 422


async def test_exception_status_filter_and_oldest_first_sort(
    db_client: AsyncClient, session: AsyncSession
) -> None:
    shipment = await _shipment(session)
    now = datetime.now(UTC)
    for kind, status, age_h in [
        (ExceptionType.DAMAGED, ExceptionStatus.OPEN, 1),
        (ExceptionType.DELAYED, ExceptionStatus.INVESTIGATING, 5),
    ]:
        session.add(
            ShipmentException(
                shipment_id=shipment.id,
                type=kind,
                severity=ExceptionSeverity.LOW,
                status=status,
                description="x",
                created_at=now - timedelta(hours=age_h),
            )
        )
    await session.flush()

    async def kinds(**params: Any) -> list[str]:
        body = (await db_client.get(f"{API}/exceptions", params=params)).json()
        return [e["type"] for e in body["items"]]

    assert await kinds(status="INVESTIGATING") == ["DELAYED"]
    assert await kinds(sort="created_at") == ["DELAYED", "DAMAGED"]  # oldest first
    assert await kinds(sort="-created_at") == ["DAMAGED", "DELAYED"]


# --- exception PATCH edge cases ---------------------------------------------------------------


@pytest.fixture
async def open_exception(session: AsyncSession) -> ShipmentException:
    shipment = await _shipment(session)
    exception = ShipmentException(
        shipment_id=shipment.id,
        type=ExceptionType.MISSING_DOCUMENT,
        severity=ExceptionSeverity.LOW,
        description="No CMR",
    )
    session.add(exception)
    await session.flush()
    return exception


async def test_exception_patch_accepts_partial_updates(
    db_client: AsyncClient, open_exception: ShipmentException
) -> None:
    url = f"{API}/exceptions/{open_exception.id}"

    severity_only = await db_client.patch(url, json={"severity": "CRITICAL"})
    note_only = await db_client.patch(url, json={"resolution_note": "carrier contacted"})
    same_status = await db_client.patch(url, json={"status": "OPEN"})

    assert (severity_only.json()["severity"], severity_only.json()["status"]) == (
        "CRITICAL",
        "OPEN",
    )
    assert note_only.json()["resolution_note"] == "carrier contacted"
    assert same_status.status_code == 200
    assert same_status.json()["status"] == "OPEN"


@pytest.mark.parametrize(
    "body",
    [{}, {"status": None}, {"severity": None}, {"status": "REOPENED"}, {"unknown": 1},
     {"resolution_note": ""}, {"resolution_note": "x" * 1001}],
)  # fmt: skip
async def test_exception_patch_rejects_invalid_bodies(
    db_client: AsyncClient, open_exception: ShipmentException, body: dict[str, Any]
) -> None:
    response = await db_client.patch(f"{API}/exceptions/{open_exception.id}", json=body)

    assert response.status_code == 422


async def test_exception_patch_unknown_id_returns_404(db_client: AsyncClient) -> None:
    response = await db_client.patch(f"{API}/exceptions/{uuid.uuid4()}", json={"severity": "LOW"})

    assert response.status_code == 404


# --- tracking event validation edges ----------------------------------------------------------


async def test_event_cannot_precede_the_shipment_and_temperature_must_be_plausible(
    db_client: AsyncClient, session: AsyncSession
) -> None:
    shipment = await _shipment(session, temperature_status=TemperatureStatus.NORMAL)
    url = f"{API}/shipments/{shipment.id}/events"
    before_creation = (datetime.now(UTC) - timedelta(days=2)).isoformat()

    too_early = await db_client.post(
        url, json={"event_type": "CHECKPOINT", "location": "A7", "occurred_at": before_creation}
    )
    absurd = await db_client.post(
        url,
        json={
            "event_type": "TEMPERATURE_ALERT",
            "location": "A7",
            "details": {"temperature_c": 500},
        },
    )

    assert too_early.status_code == 422
    assert too_early.json()["error"]["code"] == "event_out_of_order"
    assert absurd.status_code == 422
    assert "between -40 and 60" in absurd.text


# --- fleet edge cases -------------------------------------------------------------------------


async def test_driver_search_and_unknown_vehicle_plate(
    db_client: AsyncClient, session: AsyncSession
) -> None:
    session.add_all(
        [
            Driver(full_name="Svenja Lorenz", license_number="DE-900"),
            Driver(full_name="Jakub Kowalski", license_number="DE-901"),
            f.make_vehicle(),
            f.make_route(),
        ]
    )
    await session.flush()

    by_name = (await db_client.get(f"{API}/drivers", params={"search": "lorenz"})).json()
    by_license = (await db_client.get(f"{API}/drivers", params={"search": "de-901"})).json()
    missing_plate = await db_client.get(f"{API}/vehicles/by-registration/NOPE")

    assert [d["full_name"] for d in by_name["items"]] == ["Svenja Lorenz"]
    assert [d["full_name"] for d in by_license["items"]] == ["Jakub Kowalski"]
    assert missing_plate.status_code == 404
