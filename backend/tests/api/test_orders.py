"""Orders API, end to end: HTTP -> router -> service -> repository -> PostgreSQL."""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.orders.models import Order, OrderPriority, OrderStatus
from tests.db import factories as f

URL = "/api/v1/orders"


def _future(hours: int = 48) -> str:
    return (datetime.now(UTC) + timedelta(hours=hours)).isoformat()


def _payload(**overrides: Any) -> dict[str, Any]:
    return {
        "customer_name": "Leinetal Pharma GmbH",
        "origin": "Garbsen",
        "destination": "Hannover",
        "priority": "HIGH",
        "promised_delivery_at": _future(),
        **overrides,
    }


async def _create(client: AsyncClient, **overrides: Any) -> dict[str, Any]:
    response = await client.post(URL, json=_payload(**overrides))
    assert response.status_code == 201, response.text
    body: dict[str, Any] = response.json()
    return body


async def _insert(session: AsyncSession, **overrides: Any) -> Order:
    """Insert directly (bypassing the API) to set up states the API wouldn't allow."""
    order = f.make_order(**overrides)
    session.add(order)
    await session.flush()
    return order


# --- create ---------------------------------------------------------------------------------


async def test_create_order(db_client: AsyncClient) -> None:
    response = await db_client.post(URL, json=_payload())

    assert response.status_code == 201
    body = response.json()
    assert body["order_number"].startswith("ORD-")
    assert body["status"] == "PENDING"
    assert body["priority"] == "HIGH"
    assert body["customer_name"] == "Leinetal Pharma GmbH"
    assert response.headers["Location"].endswith(f"/api/v1/orders/{body['id']}")


async def test_order_numbers_are_unique_and_increasing(db_client: AsyncClient) -> None:
    first = await _create(db_client)
    second = await _create(db_client)

    assert int(second["order_number"][4:]) > int(first["order_number"][4:])


async def test_created_order_can_be_fetched(db_client: AsyncClient) -> None:
    created = await _create(db_client)

    by_id = await db_client.get(f"{URL}/{created['id']}")
    by_number = await db_client.get(f"{URL}/by-number/{created['order_number']}")

    assert by_id.json() == created
    assert by_number.json() == created


@pytest.mark.parametrize(
    ("overrides", "field"),
    [
        ({"customer_name": ""}, "customer_name"),
        ({"destination": "x" * 81}, "destination"),
        ({"priority": "SUPER_URGENT"}, "priority"),
        ({"promised_delivery_at": "not-a-date"}, "promised_delivery_at"),
        ({"status": "DELIVERED"}, "status"),  # not settable on create
    ],
)
async def test_create_validation_errors(
    db_client: AsyncClient, overrides: dict[str, Any], field: str
) -> None:
    response = await db_client.post(URL, json=_payload(**overrides))

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "validation_error"
    assert any(field in detail["location"] for detail in error["details"])


async def test_create_rejects_past_delivery_date(db_client: AsyncClient) -> None:
    response = await db_client.post(URL, json=_payload(promised_delivery_at=_future(-1)))

    assert response.status_code == 422
    assert "in the future" in response.text


async def test_create_requires_all_fields(db_client: AsyncClient) -> None:
    response = await db_client.post(URL, json={})

    missing = {d["location"][-1] for d in response.json()["error"]["details"]}
    assert missing == {"customer_name", "origin", "destination", "promised_delivery_at"}


# --- read / missing resource ----------------------------------------------------------------


async def test_get_missing_order_returns_404(db_client: AsyncClient) -> None:
    response = await db_client.get(f"{URL}/{uuid.uuid4()}")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


async def test_get_missing_order_by_number_returns_404(db_client: AsyncClient) -> None:
    assert (await db_client.get(f"{URL}/by-number/ORD-00000")).status_code == 404


async def test_malformed_id_returns_422(db_client: AsyncClient) -> None:
    assert (await db_client.get(f"{URL}/not-a-uuid")).status_code == 422


# --- list: filtering, sorting, pagination -----------------------------------------------------


async def test_filter_by_status_and_priority(db_client: AsyncClient, session: AsyncSession) -> None:
    await _insert(session, status=OrderStatus.CONFIRMED, priority=OrderPriority.URGENT)
    await _insert(session, status=OrderStatus.CONFIRMED, priority=OrderPriority.LOW)
    await _insert(session, status=OrderStatus.CANCELLED, priority=OrderPriority.URGENT)

    response = await db_client.get(URL, params={"status": "CONFIRMED", "priority": "URGENT"})

    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["status"] == "CONFIRMED"
    assert body["items"][0]["priority"] == "URGENT"


async def test_filter_accepts_repeated_values(
    db_client: AsyncClient, session: AsyncSession
) -> None:
    for status in (OrderStatus.PENDING, OrderStatus.CONFIRMED, OrderStatus.CANCELLED):
        await _insert(session, status=status)

    response = await db_client.get(URL, params=[("status", "PENDING"), ("status", "CONFIRMED")])

    assert {o["status"] for o in response.json()["items"]} == {"PENDING", "CONFIRMED"}


async def test_filter_destination_is_case_insensitive(
    db_client: AsyncClient, session: AsyncSession
) -> None:
    await _insert(session, destination="Hannover")
    await _insert(session, destination="Hamburg")

    response = await db_client.get(URL, params={"destination": "hannover"})

    assert [o["destination"] for o in response.json()["items"]] == ["Hannover"]


async def test_search_matches_customer_and_treats_wildcards_literally(
    db_client: AsyncClient, session: AsyncSession
) -> None:
    await _insert(session, customer_name="Weserland Foods AG")
    await _insert(session, customer_name="100% Organic GmbH")
    await _insert(session, customer_name="1000 Organic Things")

    weser = await db_client.get(URL, params={"search": "weserland"})
    percent = await db_client.get(URL, params={"search": "100%"})

    assert [o["customer_name"] for o in weser.json()["items"]] == ["Weserland Foods AG"]
    # "%" must not act as a wildcard: "1000 Organic Things" must not match.
    assert [o["customer_name"] for o in percent.json()["items"]] == ["100% Organic GmbH"]


async def test_filter_by_created_range(db_client: AsyncClient, session: AsyncSession) -> None:
    now = datetime.now(UTC)
    old = await _insert(session, created_at=now - timedelta(days=10))
    recent = await _insert(session, created_at=now - timedelta(hours=1))

    response = await db_client.get(
        URL, params={"created_after": (now - timedelta(days=1)).isoformat()}
    )

    ids = {o["id"] for o in response.json()["items"]}
    assert str(recent.id) in ids
    assert str(old.id) not in ids


async def test_pagination(db_client: AsyncClient, session: AsyncSession) -> None:
    for _ in range(5):
        await _insert(session)

    first = (await db_client.get(URL, params={"limit": 2, "offset": 0})).json()
    second = (await db_client.get(URL, params={"limit": 2, "offset": 2})).json()
    last = (await db_client.get(URL, params={"limit": 2, "offset": 4})).json()

    assert first["total"] == second["total"] == 5
    assert (len(first["items"]), len(second["items"]), len(last["items"])) == (2, 2, 1)
    seen = [o["id"] for page in (first, second, last) for o in page["items"]]
    assert len(set(seen)) == 5  # no duplicates, nothing skipped


async def test_sort_by_priority_uses_business_order(
    db_client: AsyncClient, session: AsyncSession
) -> None:
    for priority in (
        OrderPriority.NORMAL,
        OrderPriority.URGENT,
        OrderPriority.LOW,
        OrderPriority.HIGH,
    ):
        await _insert(session, priority=priority)

    response = await db_client.get(URL, params={"sort": "-priority"})

    assert [o["priority"] for o in response.json()["items"]] == ["URGENT", "HIGH", "NORMAL", "LOW"]


async def test_sort_by_promised_delivery_ascending(
    db_client: AsyncClient, session: AsyncSession
) -> None:
    now = datetime.now(UTC)
    for days in (3, 1, 2):
        await _insert(session, promised_delivery_at=now + timedelta(days=days))

    items = (await db_client.get(URL, params={"sort": "promised_delivery_at"})).json()["items"]

    dates = [o["promised_delivery_at"] for o in items]
    assert dates == sorted(dates)


@pytest.mark.parametrize(
    "params",
    [
        {"limit": 0},
        {"limit": 101},
        {"offset": -1},
        {"sort": "password"},  # only whitelisted sort keys
        {"status": "TELEPORTED"},
        {"colour": "blue"},  # unknown parameter
        {"created_after": "2026-10-02T00:00:00Z", "created_before": "2026-10-01T00:00:00Z"},
    ],
)
async def test_invalid_list_params_return_422(
    db_client: AsyncClient, params: dict[str, Any]
) -> None:
    assert (await db_client.get(URL, params=params)).status_code == 422


# --- update ---------------------------------------------------------------------------------


async def test_update_changes_only_given_fields(db_client: AsyncClient) -> None:
    created = await _create(db_client)

    response = await db_client.patch(f"{URL}/{created['id']}", json={"priority": "URGENT"})

    assert response.status_code == 200
    updated = response.json()
    assert updated["priority"] == "URGENT"
    assert updated["customer_name"] == created["customer_name"]
    assert updated["updated_at"] >= created["updated_at"]


async def test_update_status_through_allowed_transitions(db_client: AsyncClient) -> None:
    order_id = (await _create(db_client))["id"]

    for status in ("CONFIRMED", "PROCESSING", "SHIPPED", "DELIVERED"):
        response = await db_client.patch(f"{URL}/{order_id}", json={"status": status})
        assert response.status_code == 200, response.text
        assert response.json()["status"] == status


async def test_update_rejects_invalid_transition(db_client: AsyncClient) -> None:
    order_id = (await _create(db_client))["id"]

    response = await db_client.patch(f"{URL}/{order_id}", json={"status": "DELIVERED"})

    assert response.status_code == 409
    error = response.json()["error"]
    assert error["code"] == "invalid_status_transition"
    assert error["details"]["allowed"] == ["CANCELLED", "CONFIRMED"]


async def test_cancelled_order_is_read_only(db_client: AsyncClient) -> None:
    order_id = (await _create(db_client))["id"]
    await db_client.patch(f"{URL}/{order_id}", json={"status": "CANCELLED"})

    response = await db_client.patch(f"{URL}/{order_id}", json={"priority": "LOW"})

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "order_not_editable"


async def test_destination_frozen_once_processing(
    db_client: AsyncClient, session: AsyncSession
) -> None:
    order = await _insert(session, status=OrderStatus.PROCESSING)

    response = await db_client.patch(f"{URL}/{order.id}", json={"destination": "Berlin"})

    assert response.status_code == 409


async def test_update_cannot_make_destination_equal_origin(db_client: AsyncClient) -> None:
    created = await _create(db_client, origin="Garbsen", destination="Hannover")

    response = await db_client.patch(f"{URL}/{created['id']}", json={"destination": "GARBSEN"})

    assert response.status_code == 409
    assert "must differ" in response.text


@pytest.mark.parametrize(
    "body", [{}, {"customer_name": None}, {"order_number": "ORD-1"}, {"priority": "MEGA"}]
)
async def test_update_validation_errors(db_client: AsyncClient, body: dict[str, Any]) -> None:
    order_id = (await _create(db_client))["id"]

    assert (await db_client.patch(f"{URL}/{order_id}", json=body)).status_code == 422


async def test_update_missing_order_returns_404(db_client: AsyncClient) -> None:
    response = await db_client.patch(f"{URL}/{uuid.uuid4()}", json={"priority": "LOW"})

    assert response.status_code == 404


# --- delete ---------------------------------------------------------------------------------


async def test_delete_order(db_client: AsyncClient) -> None:
    order_id = (await _create(db_client))["id"]

    response = await db_client.delete(f"{URL}/{order_id}")

    assert response.status_code == 204
    assert response.content == b""
    assert (await db_client.get(f"{URL}/{order_id}")).status_code == 404


async def test_delete_missing_order_returns_404(db_client: AsyncClient) -> None:
    assert (await db_client.delete(f"{URL}/{uuid.uuid4()}")).status_code == 404


async def test_order_with_shipments_cannot_be_deleted(
    db_client: AsyncClient, session: AsyncSession
) -> None:
    order = await _insert(session)
    warehouse = f.make_warehouse()
    session.add(warehouse)
    await session.flush()
    session.add(f.make_shipment(order, warehouse))
    await session.flush()

    response = await db_client.delete(f"{URL}/{order.id}")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "order_has_shipments"
    assert (await db_client.get(f"{URL}/{order.id}")).status_code == 200
