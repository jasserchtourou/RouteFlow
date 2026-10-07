"""Warehouses + inventory API against real PostgreSQL."""

import uuid
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.warehouses.models import (
    DockDirection,
    DockStatus,
    EquipmentStatus,
    EquipmentType,
    Warehouse,
    WarehouseStatus,
)
from tests.db import factories as f

API = "/api/v1"


async def _warehouse(session: AsyncSession, **overrides: Any) -> Warehouse:
    warehouse = f.make_warehouse(**overrides)
    session.add(warehouse)
    await session.flush()
    return warehouse


async def _stock(
    session: AsyncSession, warehouse: Warehouse, sku: str, available: int, threshold: int
) -> None:
    session.add(
        f.make_inventory_item(
            warehouse,
            sku=sku,
            quantity=available + 5,
            reserved_quantity=5,
            reorder_threshold=threshold,
        )
    )
    await session.flush()


# --- warehouses -----------------------------------------------------------------------------


async def test_list_warehouses_with_utilization_and_stock_counts(
    db_client: AsyncClient, session: AsyncSession
) -> None:
    site = await _warehouse(session, code="WH-A", capacity=200, current_utilization=192)
    await _stock(session, site, "A-1", available=0, threshold=10)  # out of stock
    await _stock(session, site, "A-2", available=5, threshold=10)  # low
    await _stock(session, site, "A-3", available=50, threshold=10)  # ok
    await _warehouse(session, code="WH-B")  # no inventory at all

    body = (await db_client.get(f"{API}/warehouses")).json()

    by_code = {w["code"]: w for w in body["items"]}
    assert body["total"] == 2
    assert by_code["WH-A"]["utilization_pct"] == 96.0
    assert by_code["WH-A"]["utilization_level"] == "CRITICAL"
    assert (by_code["WH-A"]["sku_count"], by_code["WH-A"]["low_stock_count"]) == (3, 2)
    assert (by_code["WH-B"]["sku_count"], by_code["WH-B"]["low_stock_count"]) == (0, 0)


async def test_filter_warehouses(db_client: AsyncClient, session: AsyncSession) -> None:
    garbsen = {"name": "Garbsen Logistics Park", "location": "Garbsen", "capacity": 100}
    hannover = {"name": "Hannover Central", "location": "Hannover", "capacity": 100}
    await _warehouse(
        session,
        code="WH-GAR",
        status=WarehouseStatus.DISRUPTED,
        current_utilization=96,
        **garbsen,
    )
    await _warehouse(session, code="WH-HAN", current_utilization=50, **hannover)

    async def codes(**params: Any) -> list[str]:
        response = await db_client.get(f"{API}/warehouses", params=params)
        return [w["code"] for w in response.json()["items"]]

    assert await codes(status="DISRUPTED") == ["WH-GAR"]
    assert await codes(utilization_level="CRITICAL") == ["WH-GAR"]
    assert await codes(location="hannover") == ["WH-HAN"]
    assert await codes(search="central") == ["WH-HAN"]


async def test_sort_warehouses_by_utilization_and_low_stock(
    db_client: AsyncClient, session: AsyncSession
) -> None:
    calm = await _warehouse(session, code="WH-1", capacity=100, current_utilization=10)
    await _warehouse(session, code="WH-2", capacity=100, current_utilization=90)
    for i in range(3):
        await _stock(session, calm, f"S-{i}", available=1, threshold=10)

    by_util = (await db_client.get(f"{API}/warehouses", params={"sort": "-utilization"})).json()
    by_stock = (await db_client.get(f"{API}/warehouses", params={"sort": "-low_stock"})).json()

    assert [w["code"] for w in by_util["items"]] == ["WH-2", "WH-1"]
    assert [w["code"] for w in by_stock["items"]] == ["WH-1", "WH-2"]


async def test_warehouse_detail_summaries(db_client: AsyncClient, session: AsyncSession) -> None:
    site = await _warehouse(session, code="WH-D")
    await _stock(session, site, "D-1", available=0, threshold=10)
    await _stock(session, site, "D-2", available=40, threshold=10)
    session.add_all(
        [
            f.make_dock(site, code="In 1", position=1),
            f.make_dock(
                site,
                code="Out 1",
                position=2,
                direction=DockDirection.OUTBOUND,
                status=DockStatus.OUT_OF_SERVICE,
            ),
            f.make_equipment(site, code="FL-01", status=EquipmentStatus.ACTIVE),
            f.make_equipment(site, code="FL-02", status=EquipmentStatus.MAINTENANCE),
        ]
    )
    await session.flush()

    by_id = (await db_client.get(f"{API}/warehouses/{site.id}")).json()
    by_code = (await db_client.get(f"{API}/warehouses/by-code/wh-d")).json()  # case-insensitive

    assert by_id == by_code
    assert by_id["inventory"] == {
        "sku_count": 2,
        "total_quantity": 50,  # (0 + 5) + (40 + 5)
        "reserved_quantity": 10,
        "available_quantity": 40,
        "low_stock_count": 1,
        "out_of_stock_count": 1,
    }
    assert by_id["docks"] == {"total": 2, "inbound": 1, "outbound": 1, "out_of_service": 1}
    assert by_id["equipment"]["total"] == 2
    assert by_id["equipment"]["by_status"] == {
        "ACTIVE": 1,
        "IDLE": 0,
        "CHARGING": 0,
        "MAINTENANCE": 1,
    }


async def test_empty_warehouse_detail_has_zero_summaries(
    db_client: AsyncClient, session: AsyncSession
) -> None:
    site = await _warehouse(session)

    body = (await db_client.get(f"{API}/warehouses/{site.id}")).json()

    assert body["inventory"]["sku_count"] == 0
    assert body["docks"]["total"] == 0
    assert body["equipment"]["total"] == 0


async def test_docks_in_facade_order_and_equipment(
    db_client: AsyncClient, session: AsyncSession
) -> None:
    site = await _warehouse(session)
    session.add_all(
        [
            f.make_dock(site, code="Out 1", position=2, direction=DockDirection.OUTBOUND),
            f.make_dock(site, code="In 1", position=1),
            f.make_equipment(site, code="RT-01", equipment_type=EquipmentType.REACH_TRUCK),
            f.make_equipment(site, code="FL-01"),
        ]
    )
    await session.flush()

    docks = (await db_client.get(f"{API}/warehouses/{site.id}/docks")).json()
    equipment = (await db_client.get(f"{API}/warehouses/{site.id}/equipment")).json()

    assert [d["code"] for d in docks] == ["In 1", "Out 1"]
    assert [e["code"] for e in equipment] == ["FL-01", "RT-01"]


@pytest.mark.parametrize(
    "path", ["/warehouses/{id}", "/warehouses/{id}/docks", "/warehouses/{id}/equipment",
             "/warehouses/{id}/inventory"],
)  # fmt: skip
async def test_unknown_warehouse_returns_404(db_client: AsyncClient, path: str) -> None:
    response = await db_client.get(API + path.format(id=uuid.uuid4()))

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


async def test_unknown_warehouse_code_returns_404(db_client: AsyncClient) -> None:
    assert (await db_client.get(f"{API}/warehouses/by-code/WH-NOPE")).status_code == 404


@pytest.mark.parametrize(
    "params", [{"sort": "capacity"}, {"utilization_level": "EXTREME"}, {"limit": 500}]
)
async def test_invalid_warehouse_params_return_422(
    db_client: AsyncClient, params: dict[str, Any]
) -> None:
    assert (await db_client.get(f"{API}/warehouses", params=params)).status_code == 422


# --- inventory ------------------------------------------------------------------------------


async def test_warehouse_inventory_listing(db_client: AsyncClient, session: AsyncSession) -> None:
    site = await _warehouse(session)
    other = await _warehouse(session)
    await _stock(session, site, "EL-1001", available=100, threshold=10)
    await _stock(session, site, "PH-4001", available=3, threshold=10)
    await _stock(session, other, "EL-1001", available=1, threshold=10)  # other site

    body = (await db_client.get(f"{API}/warehouses/{site.id}/inventory")).json()

    assert body["total"] == 2
    pharma = next(i for i in body["items"] if i["sku"] == "PH-4001")
    assert pharma["available_quantity"] == 3
    assert pharma["reserved_quantity"] == 5
    assert pharma["stock_status"] == "LOW"
    assert pharma["coverage_ratio"] == 0.3


async def test_inventory_filters_and_sorting(db_client: AsyncClient, session: AsyncSession) -> None:
    site = await _warehouse(session)
    await _stock(session, site, "A-OK", available=100, threshold=10)
    await _stock(session, site, "B-LOW", available=8, threshold=10)
    await _stock(session, site, "C-LOWER", available=2, threshold=10)
    await _stock(session, site, "D-OUT", available=0, threshold=10)
    url = f"{API}/warehouses/{site.id}/inventory"

    low = (await db_client.get(url, params={"stock_status": "LOW"})).json()
    urgent_first = (await db_client.get(url, params={"sort": "coverage"})).json()
    search = (await db_client.get(url, params={"search": "low"})).json()

    assert {i["sku"] for i in low["items"]} == {"B-LOW", "C-LOWER"}
    assert [i["sku"] for i in urgent_first["items"]] == ["D-OUT", "C-LOWER", "B-LOW", "A-OK"]
    assert {i["sku"] for i in search["items"]} == {"B-LOW", "C-LOWER"}


async def test_low_stock_across_warehouses(db_client: AsyncClient, session: AsyncSession) -> None:
    garbsen = await _warehouse(session, code="WH-GAR", name="Garbsen Logistics Park")
    hannover = await _warehouse(session, code="WH-HAN", name="Hannover Central")
    await _stock(session, garbsen, "G-1", available=1, threshold=20)
    await _stock(session, garbsen, "G-2", available=0, threshold=20)
    await _stock(session, hannover, "H-1", available=9, threshold=10)
    await _stock(session, hannover, "H-OK", available=99, threshold=10)

    body = (await db_client.get(f"{API}/inventory/low-stock")).json()

    assert [i["sku"] for i in body["items"]] == ["G-2", "G-1", "H-1"]  # most urgent first
    first = body["items"][0]
    assert first["warehouse_code"] == "WH-GAR"
    assert first["warehouse_name"] == "Garbsen Logistics Park"
    assert first["shortfall"] == 21  # 20 - 0 + 1


async def test_low_stock_filters(db_client: AsyncClient, session: AsyncSession) -> None:
    garbsen = await _warehouse(session, code="WH-GAR")
    hannover = await _warehouse(session, code="WH-HAN")
    await _stock(session, garbsen, "G-OUT", available=0, threshold=10)
    await _stock(session, garbsen, "G-LOW", available=5, threshold=10)
    await _stock(session, hannover, "H-LOW", available=5, threshold=10)
    url = f"{API}/inventory/low-stock"

    only_garbsen = (await db_client.get(url, params={"warehouse_code": "wh-gar"})).json()
    without_out = (await db_client.get(url, params={"include_out_of_stock": "false"})).json()

    assert {i["sku"] for i in only_garbsen["items"]} == {"G-OUT", "G-LOW"}
    assert {i["sku"] for i in without_out["items"]} == {"G-LOW", "H-LOW"}


async def test_low_stock_pagination(db_client: AsyncClient, session: AsyncSession) -> None:
    site = await _warehouse(session)
    for i in range(5):
        await _stock(session, site, f"P-{i}", available=i, threshold=10)

    first = (await db_client.get(f"{API}/inventory/low-stock", params={"limit": 3})).json()
    rest = (
        await db_client.get(f"{API}/inventory/low-stock", params={"limit": 3, "offset": 3})
    ).json()

    assert first["total"] == 5
    assert len(first["items"]) + len(rest["items"]) == 5
    assert {i["sku"] for i in first["items"]}.isdisjoint({i["sku"] for i in rest["items"]})
