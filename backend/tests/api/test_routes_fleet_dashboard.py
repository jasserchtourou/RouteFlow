"""Routes, fleet, drivers and dashboard against real PostgreSQL."""

import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import get_clock
from app.modules.drivers.models import Driver, DriverStatus
from app.modules.exceptions.models import (
    ExceptionSeverity,
    ExceptionStatus,
    ExceptionType,
    ShipmentException,
)
from app.modules.orders.models import Order, OrderStatus
from app.modules.routes.models import RiskLevel, Route, RouteStatus
from app.modules.shipments.models import Shipment, ShipmentStatus
from app.modules.vehicles.models import Vehicle, VehicleStatus, VehicleType
from app.modules.warehouses.models import Warehouse
from tests.db import factories as f

API = "/api/v1"


class Builder:
    """Creates related test data with as little ceremony as possible."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.warehouse: Warehouse | None = None

    async def add(self, *objects: Any) -> None:
        self.session.add_all(objects)
        await self.session.flush()

    async def site(self, **overrides: Any) -> Warehouse:
        warehouse = f.make_warehouse(**overrides)
        await self.add(warehouse)
        self.warehouse = self.warehouse or warehouse
        return warehouse

    async def route(self, **overrides: Any) -> Route:
        route = f.make_route(**overrides)
        await self.add(route)
        return route

    async def shipment(
        self,
        *,
        route: Route | None = None,
        vehicle: Vehicle | None = None,
        status: ShipmentStatus = ShipmentStatus.IN_TRANSIT,
        late_minutes: int = 0,
        promised: datetime | None = None,
        **overrides: Any,
    ) -> Shipment:
        warehouse = self.warehouse or await self.site()
        order = f.make_order(
            status=OrderStatus.SHIPPED,
            promised_delivery_at=promised or datetime.now(UTC) + timedelta(days=1),
        )
        await self.add(order)
        eta = datetime.now(UTC) + (
            -timedelta(minutes=late_minutes) if late_minutes else timedelta(hours=3)
        )
        shipment = f.make_shipment(
            order,
            warehouse,
            status=status,
            estimated_delivery=eta,
            route_id=route.id if route else None,
            vehicle_id=vehicle.id if vehicle else None,
            **overrides,
        )
        await self.add(shipment)
        return shipment

    async def incident(self, shipment: Shipment, severity: ExceptionSeverity) -> None:
        await self.add(
            ShipmentException(
                shipment_id=shipment.id,
                type=ExceptionType.DELAYED,
                severity=severity,
                description="x",
            )
        )


@pytest.fixture
def build(session: AsyncSession) -> Builder:
    return Builder(session)


@pytest.fixture
def frozen_clock(app: FastAPI) -> Iterator[list[datetime]]:
    """Freeze the dashboard clock; tests set `frozen_clock[0]` to the moment they want."""
    moment = [datetime.now(UTC)]
    app.dependency_overrides[get_clock] = lambda: lambda: moment[0]
    yield moment
    app.dependency_overrides.pop(get_clock, None)


# --- routes ---------------------------------------------------------------------------------


async def test_route_list_includes_live_stats_and_risk(
    db_client: AsyncClient, build: Builder
) -> None:
    route = await build.route(route_number="RTE-900", risk_level=RiskLevel.MEDIUM)
    late = await build.shipment(route=route, late_minutes=130)
    await build.shipment(route=route)
    await build.shipment(
        route=route, status=ShipmentStatus.DELIVERED, actual_delivery=datetime.now(UTC)
    )
    await build.incident(late, ExceptionSeverity.HIGH)

    item = (await db_client.get(f"{API}/routes")).json()["items"][0]

    assert item["route_number"] == "RTE-900"
    assert (item["active_shipments"], item["delayed_shipments"]) == (2, 1)
    assert item["max_delay_minutes"] in (129, 130, 131)
    assert item["serious_exceptions"] == 1
    assert item["planned_risk_level"] == "MEDIUM"
    assert item["risk"]["score"] == 25 + 5 + 6 + 10
    assert "1 of 2 active shipments delayed (+5)" in item["risk"]["factors"]


async def test_resolved_or_minor_exceptions_do_not_count_as_serious(
    db_client: AsyncClient, build: Builder, session: AsyncSession
) -> None:
    route = await build.route()
    shipment = await build.shipment(route=route)
    await build.incident(shipment, ExceptionSeverity.LOW)
    await build.add(
        ShipmentException(
            shipment_id=shipment.id,
            type=ExceptionType.DAMAGED,
            severity=ExceptionSeverity.CRITICAL,
            status=ExceptionStatus.RESOLVED,
            description="x",
            resolved_at=datetime.now(UTC),
            resolution_note="fixed",
        )
    )

    item = (await db_client.get(f"{API}/routes/{route.id}")).json()

    assert item["serious_exceptions"] == 0


async def test_delayed_route_filter(db_client: AsyncClient, build: Builder) -> None:
    flagged = await build.route(route_number="RTE-901", status=RouteStatus.DELAYED)
    carrying_late = await build.route(route_number="RTE-902")
    await build.shipment(route=carrying_late, late_minutes=30)
    await build.route(route_number="RTE-903")  # calm

    delayed = (await db_client.get(f"{API}/routes", params={"delayed": "true"})).json()
    calm = (await db_client.get(f"{API}/routes", params={"delayed": "false"})).json()

    assert {r["route_number"] for r in delayed["items"]} == {
        flagged.route_number,
        carrying_late.route_number,
    }
    assert [r["route_number"] for r in calm["items"]] == ["RTE-903"]


async def test_route_filters_and_sorting(db_client: AsyncClient, build: Builder) -> None:
    await build.route(
        route_number="RTE-1",
        origin="Garbsen",
        destination="Hannover",
        distance_km=18,
        risk_level=RiskLevel.HIGH,
        status=RouteStatus.ACTIVE,
    )
    await build.route(
        route_number="RTE-2",
        origin="Hamburg",
        destination="Hannover",
        distance_km=155,
        risk_level=RiskLevel.LOW,
        status=RouteStatus.ACTIVE,
    )
    await build.route(
        route_number="RTE-3",
        origin="Berlin",
        destination="Leipzig",
        distance_km=190,
        status=RouteStatus.PLANNED,
    )

    async def numbers(**params: Any) -> list[str]:
        body = (await db_client.get(f"{API}/routes", params=params)).json()
        return [r["route_number"] for r in body["items"]]

    assert await numbers(destination="hannover") == ["RTE-1", "RTE-2"]
    assert await numbers(origin="Berlin") == ["RTE-3"]
    assert await numbers(status="PLANNED") == ["RTE-3"]
    assert await numbers(planned_risk_level="HIGH") == ["RTE-1"]
    assert await numbers(search="hamburg") == ["RTE-2"]
    assert await numbers(sort="-distance") == ["RTE-3", "RTE-2", "RTE-1"]
    assert (await numbers(sort="-planned_risk"))[0] == "RTE-1"


async def test_route_detail_lists_active_shipments_most_overdue_first(
    db_client: AsyncClient, build: Builder
) -> None:
    route = await build.route(route_number="RTE-910")
    on_time = await build.shipment(route=route)
    very_late = await build.shipment(route=route, late_minutes=200)
    await build.shipment(
        route=route, status=ShipmentStatus.DELIVERED, actual_delivery=datetime.now(UTC)
    )

    by_id = (await db_client.get(f"{API}/routes/{route.id}")).json()
    by_number = (await db_client.get(f"{API}/routes/by-number/rte-910")).json()

    assert by_id == by_number
    assert [s["shipment_number"] for s in by_id["shipments"]] == [
        very_late.shipment_number,
        on_time.shipment_number,
    ]


async def test_at_risk_ranks_by_computed_score(db_client: AsyncClient, build: Builder) -> None:
    # Planned LOW, but reality is bad: should outrank a planned-HIGH route with no problems.
    troubled = await build.route(
        route_number="RTE-920", risk_level=RiskLevel.LOW, status=RouteStatus.DELAYED
    )
    for minutes in (60, 120, 240):
        late = await build.shipment(route=troubled, late_minutes=minutes)
    await build.incident(late, ExceptionSeverity.CRITICAL)
    await build.route(route_number="RTE-921", risk_level=RiskLevel.HIGH)  # quiet
    await build.route(route_number="RTE-922", risk_level=RiskLevel.LOW)  # below MEDIUM
    await build.route(
        route_number="RTE-923", risk_level=RiskLevel.CRITICAL, status=RouteStatus.COMPLETED
    )  # finished: excluded

    ranked = (await db_client.get(f"{API}/routes/at-risk")).json()

    assert [r["route_number"] for r in ranked] == ["RTE-920", "RTE-921"]
    assert ranked[0]["risk"]["level"] in ("HIGH", "CRITICAL")
    assert ranked[0]["risk"]["score"] > ranked[1]["risk"]["score"]


async def test_at_risk_limit_and_min_level(db_client: AsyncClient, build: Builder) -> None:
    for i, level in enumerate([RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL]):
        await build.route(route_number=f"RTE-93{i}", risk_level=level)

    top_one = (await db_client.get(f"{API}/routes/at-risk", params={"limit": 1})).json()
    low_and_up = (await db_client.get(f"{API}/routes/at-risk", params={"min_level": "LOW"})).json()

    assert [r["route_number"] for r in top_one] == ["RTE-932"]
    assert len(low_and_up) == 3


async def test_unknown_route_returns_404(db_client: AsyncClient) -> None:
    assert (await db_client.get(f"{API}/routes/{uuid.uuid4()}")).status_code == 404
    assert (await db_client.get(f"{API}/routes/by-number/RTE-0")).status_code == 404


# --- vehicles / drivers / fleet -------------------------------------------------------------


async def test_vehicle_with_driver_position_and_load(
    db_client: AsyncClient, build: Builder
) -> None:
    driver = Driver(full_name="Lena Hoffmann", license_number="DE-T1")
    await build.add(driver)
    truck = f.make_vehicle(
        registration="H-RF 7777",
        status=VehicleStatus.IN_TRANSIT,
        vehicle_type=VehicleType.REFRIGERATED_TRUCK,
        current_latitude=52.37,
        current_longitude=9.73,
        fuel_level=12.5,
        driver_id=driver.id,
    )
    await build.add(truck)
    later = await build.shipment(vehicle=truck)
    sooner = await build.shipment(vehicle=truck, late_minutes=10)
    await build.shipment(
        vehicle=truck, status=ShipmentStatus.DELIVERED, actual_delivery=datetime.now(UTC)
    )  # delivered: not on board

    by_id = (await db_client.get(f"{API}/vehicles/{truck.id}")).json()
    by_plate = (await db_client.get(f"{API}/vehicles/by-registration/h-rf 7777")).json()

    assert by_id == by_plate
    assert by_id["driver_name"] == "Lena Hoffmann"
    assert by_id["position"] == {"latitude": 52.37, "longitude": 9.73}
    assert by_id["low_fuel"] is True
    assert by_id["active_shipments"] == [sooner.shipment_number, later.shipment_number]


async def test_vehicle_without_position_or_driver(db_client: AsyncClient, build: Builder) -> None:
    van = f.make_vehicle(current_latitude=None, current_longitude=None)
    await build.add(van)

    body = (await db_client.get(f"{API}/vehicles/{van.id}")).json()

    assert body["position"] is None
    assert body["driver_name"] is None
    assert body["active_shipments"] == []


async def test_vehicle_filters_and_fuel_sort(db_client: AsyncClient, build: Builder) -> None:
    await build.add(
        f.make_vehicle(registration="B-1", fuel_level=80, status=VehicleStatus.AVAILABLE),
        f.make_vehicle(registration="B-2", fuel_level=10, status=VehicleStatus.IN_TRANSIT),
        f.make_vehicle(
            registration="B-3",
            fuel_level=45,
            status=VehicleStatus.MAINTENANCE,
            vehicle_type=VehicleType.TRUCK,
        ),
    )

    async def plates(**params: Any) -> list[str]:
        body = (await db_client.get(f"{API}/vehicles", params=params)).json()
        return [v["registration"] for v in body["items"]]

    assert await plates(low_fuel="true") == ["B-2"]
    assert await plates(status="MAINTENANCE") == ["B-3"]
    assert await plates(vehicle_type="TRUCK") == ["B-3"]
    assert await plates(sort="fuel") == ["B-2", "B-3", "B-1"]
    assert await plates(search="b-2") == ["B-2"]


async def test_fleet_overview(db_client: AsyncClient, build: Builder) -> None:
    await build.add(
        f.make_vehicle(status=VehicleStatus.IN_TRANSIT, fuel_level=15),
        f.make_vehicle(status=VehicleStatus.IN_TRANSIT),
        f.make_vehicle(status=VehicleStatus.AVAILABLE),
        f.make_vehicle(status=VehicleStatus.MAINTENANCE),
        Driver(full_name="A", license_number="DE-T2", status=DriverStatus.ON_DUTY),
    )

    body = (await db_client.get(f"{API}/fleet/overview")).json()

    assert body["total"] == 4
    assert body["by_status"] == {"AVAILABLE": 1, "IN_TRANSIT": 2, "MAINTENANCE": 1, "OFFLINE": 0}
    assert body["operational"] == 3
    assert body["utilization_pct"] == 66.7
    assert body["low_fuel"] == 1
    assert body["drivers_by_status"]["ON_DUTY"] == 1


async def test_drivers_list_with_assigned_vehicle(db_client: AsyncClient, build: Builder) -> None:
    assigned = Driver(full_name="Murat Yilmaz", license_number="DE-T3", status=DriverStatus.ON_DUTY)
    spare = Driver(full_name="Anja Fuchs", license_number="DE-T4")
    await build.add(assigned, spare)
    await build.add(f.make_vehicle(registration="KS-RF 1", driver_id=assigned.id))

    body = (await db_client.get(f"{API}/drivers")).json()
    on_duty = (await db_client.get(f"{API}/drivers", params={"status": "ON_DUTY"})).json()
    one = (await db_client.get(f"{API}/drivers/{assigned.id}")).json()

    assert [d["full_name"] for d in body["items"]] == ["Anja Fuchs", "Murat Yilmaz"]
    assert [d["full_name"] for d in on_duty["items"]] == ["Murat Yilmaz"]
    assert one["vehicle_registration"] == "KS-RF 1"
    assert (await db_client.get(f"{API}/drivers/{uuid.uuid4()}")).status_code == 404


# --- dashboard ------------------------------------------------------------------------------


async def test_dashboard_overview_counts(
    db_client: AsyncClient, build: Builder, frozen_clock: list[datetime]
) -> None:
    await build.site(capacity=1000, current_utilization=960)  # critical
    await build.site(capacity=3000, current_utilization=1500)
    late = await build.shipment(late_minutes=45)
    await build.shipment(status=ShipmentStatus.OUT_FOR_DELIVERY)
    await build.shipment(status=ShipmentStatus.PICKED)
    await build.incident(late, ExceptionSeverity.CRITICAL)
    await build.add(f.make_vehicle(status=VehicleStatus.IN_TRANSIT))

    body = (await db_client.get(f"{API}/dashboard/overview")).json()

    assert body["timezone"] == "Europe/Berlin"
    assert body["shipments"]["total"] == 3
    assert body["shipments"]["in_transit"] == 2
    assert body["shipments"]["delayed"] == 1
    assert body["exceptions"] == {
        "active": 1,
        "critical": 1,
        "by_severity": {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 1},
        "by_type": {
            "DELAYED": 1,
            "TEMPERATURE_DEVIATION": 0,
            "DAMAGED": 0,
            "MISSING_DOCUMENT": 0,
            "STOCK_SHORTAGE": 0,
        },
    }
    assert body["orders"]["open"] == 3
    assert body["fleet"]["by_status"]["IN_TRANSIT"] == 1
    assert body["warehouses"]["count"] == 2
    assert body["warehouses"]["network_utilization_pct"] == 61.5  # 2460 / 4000, weighted
    assert body["warehouses"]["critical_utilization"] == 1


async def test_delivery_performance_today_vs_yesterday_in_business_time(
    db_client: AsyncClient, build: Builder, frozen_clock: list[datetime]
) -> None:
    # Now = 7 Oct, 10:00 Berlin. "Today" started at 6 Oct 22:00 UTC.
    frozen_clock[0] = datetime(2026, 10, 7, 8, 0, tzinfo=UTC)

    async def delivered(at: datetime, *, on_time: bool) -> None:
        promised = at + timedelta(minutes=30) if on_time else at - timedelta(minutes=30)
        await build.shipment(status=ShipmentStatus.DELIVERED, actual_delivery=at, promised=promised)

    await delivered(datetime(2026, 10, 6, 22, 30, tzinfo=UTC), on_time=True)  # 00:30 local today
    await delivered(datetime(2026, 10, 7, 6, 0, tzinfo=UTC), on_time=False)  # today, late
    await delivered(datetime(2026, 10, 6, 21, 30, tzinfo=UTC), on_time=True)  # 23:30 yesterday
    await delivered(datetime(2026, 10, 6, 9, 0, tzinfo=UTC), on_time=True)  # yesterday
    await delivered(datetime(2026, 10, 1, 9, 0, tzinfo=UTC), on_time=False)  # 6 days ago

    perf = (await db_client.get(f"{API}/dashboard/overview")).json()["delivery_performance"]

    assert perf["today"] == {"delivered": 2, "on_time": 1, "on_time_rate": 50.0}
    assert perf["yesterday"] == {"delivered": 2, "on_time": 2, "on_time_rate": 100.0}
    assert perf["last_7_days"] == {"delivered": 5, "on_time": 3, "on_time_rate": 60.0}
    assert perf["change_vs_yesterday_pts"] == -50.0


async def test_dashboard_on_empty_database(
    db_client: AsyncClient, frozen_clock: list[datetime]
) -> None:
    body = (await db_client.get(f"{API}/dashboard/overview")).json()

    assert body["orders"]["total"] == 0
    assert body["warehouses"]["network_utilization_pct"] is None
    assert body["fleet"]["utilization_pct"] is None
    assert body["delivery_performance"]["today"]["on_time_rate"] is None
    assert body["delivery_performance"]["change_vs_yesterday_pts"] is None


async def test_order_counts_use_business_day(
    db_client: AsyncClient, session: AsyncSession, frozen_clock: list[datetime]
) -> None:
    frozen_clock[0] = datetime(2026, 10, 7, 8, 0, tzinfo=UTC)
    session.add_all(
        [
            Order(**_order_values(created_at=datetime(2026, 10, 6, 22, 15, tzinfo=UTC))),  # today
            Order(**_order_values(created_at=datetime(2026, 10, 6, 21, 45, tzinfo=UTC))),  # before
        ]
    )
    await session.flush()

    body = (await db_client.get(f"{API}/dashboard/overview")).json()

    assert body["orders"]["created_today"] == 1


def _order_values(**overrides: Any) -> dict[str, Any]:
    order = f.make_order(**overrides)
    return {
        c: getattr(order, c)
        for c in (
            "order_number",
            "customer_name",
            "origin",
            "destination",
            "promised_delivery_at",
            "created_at",
        )
    }
