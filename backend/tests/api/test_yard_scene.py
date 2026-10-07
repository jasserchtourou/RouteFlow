"""Yard scene API and simulator against real PostgreSQL, with a frozen clock."""

import uuid
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import get_clock
from app.core.config import Settings, get_settings
from app.modules.orders.models import OrderStatus
from app.modules.shipments.models import ShipmentStatus
from app.modules.warehouses.models import (
    Dock,
    DockDirection,
    DockStatus,
    EquipmentStatus,
    Warehouse,
)
from app.modules.yard.models import DockAppointment
from tests.db import factories as f

API = "/api/v1"
NOW = datetime(2026, 10, 7, 12, 0, tzinfo=UTC)  # 14:00 in Berlin
Freeze = Callable[[datetime], None]


@pytest.fixture
def freeze(app: FastAPI) -> Freeze:
    moment = [NOW]
    app.dependency_overrides[get_clock] = lambda: lambda: moment[0]

    def set_time(value: datetime) -> None:
        moment[0] = value

    return set_time


@pytest.fixture
def simulation_off(app: FastAPI) -> None:
    app.dependency_overrides[get_settings] = lambda: Settings(
        _env_file=None, yard_simulation_enabled=False
    )


class Site:
    def __init__(self, session: AsyncSession, warehouse: Warehouse, docks: dict[str, Dock]) -> None:
        self.session = session
        self.warehouse = warehouse
        self.docks = docks

    async def visit(
        self,
        dock: str,
        *,
        arrives: float,
        docked: float,
        departs: float,
        pallets: int = 10,
        sequence: int = 0,
        shipment_id: uuid.UUID | None = None,
        **overrides: Any,
    ) -> DockAppointment:
        """A visit with timestamps given in minutes relative to NOW."""
        appointment = DockAppointment(
            warehouse_id=self.warehouse.id,
            dock_id=self.docks[dock].id,
            shipment_id=shipment_id,
            sequence=sequence,
            truck_code=f"TRK-{2000 + sequence}",
            carrier="Test Carrier",
            direction=self.docks[dock].direction,
            arrives_at=NOW + timedelta(minutes=arrives),
            docked_at=NOW + timedelta(minutes=docked),
            departs_at=NOW + timedelta(minutes=departs),
            pallets_total=pallets,
            **overrides,
        )
        self.session.add(appointment)
        await self.session.flush()
        return appointment


@pytest.fixture
async def site(session: AsyncSession) -> Site:
    warehouse = f.make_warehouse(code="WH-YARD", capacity=1000, current_utilization=640)
    session.add(warehouse)
    await session.flush()
    docks = {
        "In 1": f.make_dock(warehouse, code="In 1", direction=DockDirection.INBOUND, position=1),
        "In 2": f.make_dock(warehouse, code="In 2", direction=DockDirection.INBOUND, position=2),
        "Out 1": f.make_dock(warehouse, code="Out 1", direction=DockDirection.OUTBOUND, position=3),
    }
    session.add_all(docks.values())
    session.add_all(
        [
            f.make_equipment(warehouse, code="FL-001", status=EquipmentStatus.ACTIVE),
            f.make_equipment(warehouse, code="FL-002", status=EquipmentStatus.IDLE),
        ]
    )
    session.add_all(
        [
            f.make_inventory_item(
                warehouse,
                sku="A-1",
                product_name="Safety Helmet",
                quantity=100,
                reserved_quantity=0,
            ),
            f.make_inventory_item(
                warehouse,
                sku="B-2",
                product_name="Gloves",
                quantity=8,
                reserved_quantity=5,
                reorder_threshold=10,
            ),
        ]
    )
    await session.flush()
    return Site(session, warehouse, docks)


def scene_url(site: Site) -> str:
    return f"{API}/warehouses/{site.warehouse.id}/scene"


async def appointment_count(session: AsyncSession) -> int:
    return await session.scalar(select(func.count()).select_from(DockAppointment)) or 0


# --- basics -----------------------------------------------------------------------------------


async def test_unknown_warehouse_is_404(db_client: AsyncClient, freeze: Freeze) -> None:
    response = await db_client.get(f"{API}/warehouses/{uuid.uuid4()}/scene")
    assert response.status_code == 404


async def test_scene_describes_the_site(
    db_client: AsyncClient, site: Site, simulation_off: None, freeze: Freeze
) -> None:
    body = (await db_client.get(scene_url(site))).json()

    assert body["warehouse"]["code"] == "WH-YARD"
    assert body["warehouse"]["stock_pallets"] == 640
    assert body["warehouse"]["utilization_pct"] == 64.0
    assert body["layout"] == {"dock_count": 3, "yard_slots": 4}
    assert body["timings"] == {
        "approach_seconds": 360,
        "docking_seconds": 60,
        "leaving_seconds": 120,
    }
    assert [d["code"] for d in body["docks"]] == ["In 1", "In 2", "Out 1"]
    assert all(d["state"] == "AVAILABLE" and d["visit_id"] is None for d in body["docks"])
    assert body["visits"] == []

    # Pallets are derived from inventory, ordered by SKU, with a pin on problem stock.
    pallets = body["pallets"]
    assert [(p["id"], p["sku"], p["slot"]) for p in pallets] == [
        ("PAL-1001", "A-1", 0),
        ("PAL-1002", "B-2", 1),
    ]
    assert [p["has_issue"] for p in pallets] == [False, True]
    assert pallets[1]["stock_status"] == "LOW"


# --- live state -------------------------------------------------------------------------------


async def test_visit_states_drive_docks_equipment_and_kpis(
    db_client: AsyncClient,
    site: Site,
    simulation_off: None,
    freeze: Freeze,
    session: AsyncSession,
) -> None:
    order = f.make_order(status=OrderStatus.PROCESSING)
    session.add(order)
    await session.flush()
    shipment = f.make_shipment(
        order, site.warehouse, status=ShipmentStatus.LOADED, destination="Hamburg"
    )
    session.add(shipment)
    await session.flush()

    # Out 1: loading, 10 minutes after docking started (work began after the 1 min docking).
    await site.visit(
        "Out 1", arrives=-12, docked=-10, departs=9, pallets=19, sequence=1, shipment_id=shipment.id
    )
    # In 1: due in 3 minutes (still on the road).
    await site.visit("In 1", arrives=1, docked=3, departs=20, sequence=2)
    # In 2: waiting in the yard for its door.
    await site.visit("In 2", arrives=-3, docked=6, departs=25, sequence=3)
    # Not visible yet / already gone.
    await site.visit("In 1", arrives=60, docked=64, departs=80, sequence=4)
    await site.visit("In 2", arrives=-60, docked=-50, departs=-30, sequence=5)

    body = (await db_client.get(scene_url(site))).json()
    visits = {v["truck_code"]: v for v in body["visits"]}
    docks = {d["code"]: d for d in body["docks"]}

    assert set(visits) == {"TRK-2001", "TRK-2002", "TRK-2003"}
    loading = visits["TRK-2001"]
    assert loading["state"] == "LOADING"
    assert loading["pallets_done"] == 9  # 9 of 18 working minutes -> half of 19, rounded down
    assert loading["minutes_remaining"] == 9
    assert loading["shipment"]["shipment_number"] == shipment.shipment_number
    assert loading["shipment"]["destination"] == "Hamburg"
    assert visits["TRK-2002"]["state"] == "EN_ROUTE"
    assert visits["TRK-2002"]["minutes_remaining"] == 3
    assert visits["TRK-2003"]["state"] == "WAITING"

    assert docks["Out 1"]["state"] == "OCCUPIED"
    assert docks["Out 1"]["visit_id"] == loading["id"]
    assert docks["In 1"]["state"] == "BOOKED"
    assert docks["In 2"]["state"] == "BOOKED"

    # The only active forklift serves the dock where pallets are moving.
    equipment = {e["code"]: e for e in body["equipment"]}
    assert equipment["FL-001"]["assigned_dock_code"] == "Out 1"
    assert equipment["FL-002"]["assigned_dock_code"] is None

    kpis = body["kpis"]
    assert kpis["stock_on_hand_pallets"] == 640
    assert kpis["trucks_on_site"] == 2  # loading + waiting; the en-route truck is not on site yet
    assert kpis["inbound_trucks_on_site"] == 1
    assert kpis["docks_occupied"] == 1
    assert kpis["docks_total"] == 3
    assert docks["Out 1"]["trucks_today"] == 1
    assert docks["In 1"]["trucks_today"] == 0  # its truck has not arrived yet
    assert docks["In 2"]["trucks_today"] == 2  # the finished one plus the waiting one


async def test_out_of_service_dock_is_reported_and_never_scheduled(
    db_client: AsyncClient, site: Site, freeze: Freeze, session: AsyncSession
) -> None:
    site.docks["In 2"].status = DockStatus.OUT_OF_SERVICE
    await session.flush()

    body = (await db_client.get(scene_url(site))).json()
    docks = {d["code"]: d for d in body["docks"]}

    assert docks["In 2"]["state"] == "OUT_OF_SERVICE"
    assert all(v["dock_code"] != "In 2" for v in body["visits"])
    assert {v["dock_code"] for v in body["visits"]} <= {"In 1", "Out 1"}


async def test_delivery_kpis_compare_the_last_30_days_with_the_30_before(
    db_client: AsyncClient,
    site: Site,
    simulation_off: None,
    freeze: Freeze,
    session: AsyncSession,
) -> None:
    async def delivered(days_ago: int, on_time: bool) -> None:
        promised = NOW - timedelta(days=days_ago) + timedelta(hours=1)
        order = f.make_order(status=OrderStatus.DELIVERED, promised_delivery_at=promised)
        session.add(order)
        await session.flush()
        actual = promised - timedelta(hours=2) if on_time else promised + timedelta(hours=2)
        session.add(
            f.make_shipment(
                order,
                site.warehouse,
                status=ShipmentStatus.DELIVERED,
                actual_delivery=actual,
                estimated_delivery=promised,
            )
        )

    for _ in range(3):
        await delivered(5, on_time=True)
    await delivered(6, on_time=False)  # last 30 days: 3 of 4 on time = 75.0 %
    await delivered(40, on_time=True)
    await delivered(41, on_time=False)  # previous 30 days: 1 of 2 = 50.0 %
    await session.flush()

    kpis = (await db_client.get(scene_url(site))).json()["kpis"]
    assert kpis["on_time_rate_30d"] == 75.0
    assert kpis["on_time_change_pts"] == 25.0


async def test_delivery_kpis_are_null_without_deliveries(
    db_client: AsyncClient, site: Site, simulation_off: None, freeze: Freeze
) -> None:
    kpis = (await db_client.get(scene_url(site))).json()["kpis"]
    assert kpis["on_time_rate_30d"] is None
    assert kpis["on_time_change_pts"] is None


# --- simulator --------------------------------------------------------------------------------


async def test_simulator_fills_the_schedule_and_is_idempotent(
    db_client: AsyncClient, site: Site, freeze: Freeze, session: AsyncSession
) -> None:
    first = (await db_client.get(scene_url(site))).json()
    count_after_first = await appointment_count(session)

    assert count_after_first > 0
    # A site that starts mid-shift has trucks on screen straight away.
    assert first["visits"], "expected visible trucks at start"
    for visit in first["visits"]:
        assert 0 <= visit["pallets_done"] <= visit["pallets_total"]
        assert visit["state"] in {
            "EN_ROUTE",
            "WAITING",
            "DOCKED",
            "LOADING",
            "UNLOADING",
            "DEPARTED",
        }

    second = (await db_client.get(scene_url(site))).json()
    assert await appointment_count(session) == count_after_first
    assert [v["id"] for v in second["visits"]] == [v["id"] for v in first["visits"]]


async def test_simulator_extends_the_schedule_as_time_passes(
    db_client: AsyncClient, site: Site, freeze: Freeze, session: AsyncSession
) -> None:
    await db_client.get(scene_url(site))
    before = await appointment_count(session)

    freeze(NOW + timedelta(hours=2))
    await db_client.get(scene_url(site))

    assert await appointment_count(session) > before


async def test_simulator_drops_visits_older_than_the_retention_period(
    db_client: AsyncClient, site: Site, freeze: Freeze, session: AsyncSession
) -> None:
    old = await site.visit("In 1", arrives=-60 * 40, docked=-60 * 40 + 4, departs=-60 * 40 + 20)
    recent = await site.visit(
        "In 1", arrives=-60 * 5, docked=-60 * 5 + 4, departs=-60 * 5 + 20, sequence=1
    )

    await db_client.get(scene_url(site))

    remaining = set(
        await session.scalars(
            select(DockAppointment.id).where(DockAppointment.dock_id == old.dock_id)
        )
    )
    assert old.id not in remaining
    assert recent.id in remaining


async def test_outbound_visits_carry_a_shipment_that_is_waiting_at_the_warehouse(
    db_client: AsyncClient, site: Site, freeze: Freeze, session: AsyncSession
) -> None:
    order = f.make_order()
    session.add(order)
    await session.flush()
    shipment = f.make_shipment(order, site.warehouse, status=ShipmentStatus.PACKED)
    session.add(shipment)
    await session.flush()

    await db_client.get(scene_url(site))

    outbound = (
        await session.scalars(
            select(DockAppointment).where(DockAppointment.direction == DockDirection.OUTBOUND)
        )
    ).all()
    inbound = (
        await session.scalars(
            select(DockAppointment).where(DockAppointment.direction == DockDirection.INBOUND)
        )
    ).all()
    assert outbound
    assert {a.shipment_id for a in outbound} == {shipment.id}
    assert {a.shipment_id for a in inbound} == {None}
