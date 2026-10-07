"""Deterministic, realistic logistics data.

Everything is derived from a fixed random seed and a reference time `now`, so a given
(seed, now) always produces the same dataset, and timestamps are relative to "now" so the
dashboard looks live. A few shipments are scripted (see SCENARIOS) so demos and the AI
evaluation have known, explainable cases.
"""

import random
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from app.modules.drivers.models import Driver, DriverStatus
from app.modules.exceptions.models import (
    ExceptionSeverity,
    ExceptionStatus,
    ExceptionType,
    ShipmentException,
)
from app.modules.inventory.models import InventoryItem
from app.modules.orders.models import Order, OrderPriority, OrderStatus
from app.modules.routes.models import RiskLevel, Route, RouteStatus
from app.modules.shipments.models import Shipment, ShipmentStatus, TemperatureStatus
from app.modules.tracking.models import TrackingEvent, TrackingEventType
from app.modules.vehicles.models import Vehicle, VehicleStatus, VehicleType
from app.modules.warehouses.models import (
    Dock,
    DockDirection,
    DockStatus,
    Equipment,
    EquipmentStatus,
    EquipmentType,
    Warehouse,
    WarehouseStatus,
)
from app.seed import reference as ref


def _uid(rng: random.Random) -> uuid.UUID:
    """Deterministic UUID4 from the seeded RNG (ids are needed before flush for FKs)."""
    return uuid.UUID(int=rng.getrandbits(128), version=4)


ORDER_COUNT = 110
BACKLOG_ORDER_COUNT = 14  # orders not yet turned into shipments (PENDING/CONFIRMED/CANCELLED)

STATUS_FLOW = list(ShipmentStatus)
STATUS_WEIGHTS = {
    ShipmentStatus.CREATED: 8,
    ShipmentStatus.PICKED: 6,
    ShipmentStatus.PACKED: 6,
    ShipmentStatus.LOADED: 8,
    ShipmentStatus.IN_TRANSIT: 30,
    ShipmentStatus.OUT_FOR_DELIVERY: 12,
    ShipmentStatus.DELIVERED: 30,
}
EVENT_FOR_STATUS = {
    ShipmentStatus.CREATED: TrackingEventType.CREATED,
    ShipmentStatus.PICKED: TrackingEventType.PICKED,
    ShipmentStatus.PACKED: TrackingEventType.PACKED,
    ShipmentStatus.LOADED: TrackingEventType.LOADED,
    ShipmentStatus.IN_TRANSIT: TrackingEventType.DEPARTED,
    ShipmentStatus.OUT_FOR_DELIVERY: TrackingEventType.OUT_FOR_DELIVERY,
    ShipmentStatus.DELIVERED: TrackingEventType.DELIVERED,
}
# Hours between order creation and shipment status, per current status (min, max).
AGE_HOURS = {
    ShipmentStatus.CREATED: (0.5, 3),
    ShipmentStatus.PICKED: (2, 6),
    ShipmentStatus.PACKED: (3, 8),
    ShipmentStatus.LOADED: (4, 10),
    ShipmentStatus.IN_TRANSIT: (3, 9),
    ShipmentStatus.OUT_FOR_DELIVERY: (5, 11),
    ShipmentStatus.DELIVERED: (2, 96),  # some delivered today, some on previous days
}
# Hours until the planned delivery for on-time shipments (min, max), per current status.
REMAINING_HOURS = {
    ShipmentStatus.CREATED: (6, 14),
    ShipmentStatus.PICKED: (5, 12),
    ShipmentStatus.PACKED: (4, 10),
    ShipmentStatus.LOADED: (2, 6),
    ShipmentStatus.IN_TRANSIT: (1, 5),
    ShipmentStatus.OUT_FOR_DELIVERY: (0.3, 2),
    ShipmentStatus.DELIVERED: (0, 0),
}
# Lane (origin, destination) -> (route status, risk). Others are ACTIVE/LOW.
LANE_CONDITIONS = {
    ("Garbsen", "Hannover"): (RouteStatus.DELAYED, RiskLevel.HIGH),
    ("Hamburg", "Hannover"): (RouteStatus.DELAYED, RiskLevel.MEDIUM),
    ("Hannover", "Hamburg"): (RouteStatus.ACTIVE, RiskLevel.MEDIUM),
    ("Kassel", "Dortmund"): (RouteStatus.ACTIVE, RiskLevel.MEDIUM),
    ("Berlin", "Leipzig"): (RouteStatus.ACTIVE, RiskLevel.MEDIUM),
    ("Leipzig", "Kassel"): (RouteStatus.PLANNED, RiskLevel.LOW),
}
HEAVY_LANES = {("Garbsen", "Hannover"): 4, ("Hannover", "Hamburg"): 3, ("Hamburg", "Hannover"): 3}


@dataclass(frozen=True)
class Scenario:
    """A scripted shipment, for demos and AI evaluation with known, explainable cases."""

    lane: tuple[str, str]
    status: ShipmentStatus
    cold: bool = False
    late: bool = False
    deviation: bool = False
    transit_delay: bool = False


# Keyed by shipment index: SHP-{2201 + index}.
SCENARIOS = {
    # SHP-2208: ordinary in-transit shipment with a short, documented delay during transit.
    7: Scenario(("Hannover", "Berlin"), ShipmentStatus.IN_TRANSIT, transit_delay=True),
    # SHP-2211: cold-chain shipment on a delayed lane with a temperature deviation.
    10: Scenario(
        ("Hamburg", "Hannover"), ShipmentStatus.IN_TRANSIT, cold=True, late=True, deviation=True
    ),
}


@dataclass
class SeedData:
    warehouses: list[Warehouse] = field(default_factory=list)
    inventory: list[InventoryItem] = field(default_factory=list)
    docks: list[Dock] = field(default_factory=list)
    equipment: list[Equipment] = field(default_factory=list)
    drivers: list[Driver] = field(default_factory=list)
    vehicles: list[Vehicle] = field(default_factory=list)
    routes: list[Route] = field(default_factory=list)
    orders: list[Order] = field(default_factory=list)
    shipments: list[Shipment] = field(default_factory=list)
    events: list[TrackingEvent] = field(default_factory=list)
    exceptions: list[ShipmentException] = field(default_factory=list)
    # Seed-time bookkeeping (not persisted)
    vehicle_home: dict[uuid.UUID, str] = field(default_factory=dict)
    vehicle_leg: dict[uuid.UUID, Shipment] = field(default_factory=dict)

    def all_objects(self) -> list[object]:
        return [
            *self.warehouses, *self.inventory, *self.docks, *self.equipment, *self.drivers, *self.vehicles, *self.routes,
            *self.orders, *self.shipments, *self.events, *self.exceptions,
        ]  # fmt: skip


def generate(now: datetime, seed: int = 42) -> SeedData:
    rng = random.Random(seed)
    data = SeedData()
    data.warehouses = _build_warehouses(rng)
    warehouse_by_city = {w.location: w for w in data.warehouses}
    data.inventory = _build_inventory(rng, data.warehouses)
    # Independent random stream: adding site infrastructure must not change the shipments,
    # events, etc. generated from `rng` afterwards.
    site_rng = random.Random(f"{seed}-site")
    data.docks, data.equipment = _build_site_infrastructure(site_rng, data.warehouses)
    data.drivers, data.vehicles = _build_fleet(rng, warehouse_by_city, data.vehicle_home)
    data.routes = _build_routes(rng)
    route_by_lane = {(r.origin, r.destination): r for r in data.routes}
    _build_shipments(rng, now, data, warehouse_by_city, route_by_lane)
    _build_backlog_orders(rng, now, data)
    _update_vehicle_positions(rng, data, warehouse_by_city)
    return data


# --- reference entities ----------------------------------------------------------------


def _build_warehouses(rng: random.Random) -> list[Warehouse]:
    return [
        Warehouse(
            id=_uid(rng),
            code=s.code,
            name=s.name,
            location=s.city,
            latitude=s.latitude,
            longitude=s.longitude,
            capacity=s.capacity,
            current_utilization=s.capacity * s.utilization_pct // 100,
            status=WarehouseStatus(s.status),
        )
        for s in ref.WAREHOUSES
    ]


def _build_inventory(rng: random.Random, warehouses: list[Warehouse]) -> list[InventoryItem]:
    items: list[InventoryItem] = []
    for warehouse in warehouses:
        # The disrupted warehouse has far more stock problems (basis for "Garbsen issue").
        low_stock_share = 0.55 if warehouse.code == "WH-GAR" else 0.15
        for sku, name, _cold, threshold in rng.sample(ref.PRODUCTS, 12):
            reserved = rng.randint(0, threshold // 2)
            if rng.random() < low_stock_share:
                available = int(threshold * rng.uniform(0.1, 0.9))
            else:
                available = int(threshold * rng.uniform(1.5, 6))
            items.append(
                InventoryItem(
                    id=_uid(rng),
                    warehouse_id=warehouse.id,
                    sku=sku,
                    product_name=name,
                    quantity=available + reserved,
                    reserved_quantity=reserved,
                    reorder_threshold=threshold,
                )
            )
    return items


def _build_site_infrastructure(
    rng: random.Random, warehouses: list[Warehouse]
) -> tuple[list[Dock], list[Equipment]]:
    """Dock doors (half inbound, half outbound) and handling equipment, sized by capacity."""
    docks: list[Dock] = []
    equipment: list[Equipment] = []
    out_of_service = {"WH-GAR": 2, "WH-HAM": 1}  # the disrupted / congested sites
    for warehouse in warehouses:
        dock_count = max(4, min(8, warehouse.capacity // 8000))
        broken = out_of_service.get(warehouse.code, 0)
        for position in range(1, dock_count + 1):
            inbound = position <= dock_count // 2
            number = position if inbound else position - dock_count // 2
            docks.append(
                Dock(
                    id=_uid(rng),
                    warehouse_id=warehouse.id,
                    code=f"{'In' if inbound else 'Out'} {number}",
                    direction=DockDirection.INBOUND if inbound else DockDirection.OUTBOUND,
                    status=DockStatus.OUT_OF_SERVICE
                    if position <= broken
                    else DockStatus.AVAILABLE,
                    position=position,
                )
            )

        fleet = [EquipmentType.FORKLIFT] * (dock_count - 1) + [EquipmentType.REACH_TRUCK] * 2
        fleet.append(EquipmentType.PALLET_JACK)
        prefixes = {
            EquipmentType.FORKLIFT: "FL",
            EquipmentType.REACH_TRUCK: "RT",
            EquipmentType.PALLET_JACK: "PJ",
        }
        counters = dict.fromkeys(prefixes, 0)
        in_maintenance = 2 if warehouse.code == "WH-GAR" else 0
        for kind in fleet:
            counters[kind] += 1
            if in_maintenance and kind == EquipmentType.FORKLIFT:
                status, in_maintenance = EquipmentStatus.MAINTENANCE, in_maintenance - 1
            else:
                status = rng.choices(list(EquipmentStatus), [50, 25, 15, 10])[0]
            battery = (
                rng.uniform(10, 40) if status == EquipmentStatus.CHARGING else rng.uniform(30, 100)
            )
            equipment.append(
                Equipment(
                    id=_uid(rng),
                    warehouse_id=warehouse.id,
                    code=f"{prefixes[kind]}-{counters[kind]:02d}",
                    equipment_type=kind,
                    status=status,
                    battery_level=round(battery, 1),
                )
            )
    return docks, equipment


def _build_fleet(
    rng: random.Random,
    warehouse_by_city: dict[str, Warehouse],
    home_cities_by_vehicle: dict[uuid.UUID, str],
) -> tuple[list[Driver], list[Vehicle]]:
    drivers: list[Driver] = []
    vehicles: list[Vehicle] = []
    home_cities = list(ref.VEHICLE_PREFIXES)
    for i, name in enumerate(ref.DRIVER_NAMES):
        home = home_cities[i % len(home_cities)]
        driver = Driver(
            id=_uid(rng),
            full_name=name,
            license_number=f"DE-{100200 + i}",
            phone=f"+49 15{rng.randint(10, 99)} {rng.randint(1000000, 9999999)}",
            status=DriverStatus.AVAILABLE,
        )
        drivers.append(driver)
        # Every 4th vehicle is refrigerated so cold-chain shipments can be served.
        if i % 4 == 0:
            vehicle_type = VehicleType.REFRIGERATED_TRUCK
        else:
            vehicle_type = rng.choice(
                [VehicleType.VAN, VehicleType.TRUCK, VehicleType.SEMI_TRAILER]
            )
        warehouse = warehouse_by_city[home]
        vehicles.append(
            Vehicle(
                id=_uid(rng),
                registration=f"{ref.VEHICLE_PREFIXES[home]}-RF {1000 + i * 37}",
                vehicle_type=vehicle_type,
                status=VehicleStatus.AVAILABLE,
                current_latitude=warehouse.latitude,
                current_longitude=warehouse.longitude,
                fuel_level=round(rng.uniform(18, 100), 1),
                driver_id=driver.id,
            )
        )
        home_cities_by_vehicle[vehicles[-1].id] = home
    # A few vehicles are out of service.
    vehicles[5].status = VehicleStatus.MAINTENANCE
    vehicles[17].status = VehicleStatus.MAINTENANCE
    vehicles[22].status = VehicleStatus.OFFLINE
    return drivers, vehicles


def _build_routes(rng: random.Random) -> list[Route]:
    routes = []
    for i, (origin, destination, km, minutes) in enumerate(ref.LANES):
        status, risk = LANE_CONDITIONS.get(
            (origin, destination), (RouteStatus.ACTIVE, RiskLevel.LOW)
        )
        routes.append(
            Route(
                id=_uid(rng),
                route_number=f"RTE-{101 + i}",
                origin=origin,
                destination=destination,
                distance_km=float(km),
                estimated_duration_minutes=minutes,
                status=status,
                risk_level=risk,
            )
        )
    return routes


# --- orders, shipments, tracking, exceptions ------------------------------------------------


def _build_shipments(
    rng: random.Random,
    now: datetime,
    data: SeedData,
    warehouse_by_city: dict[str, Warehouse],
    route_by_lane: dict[tuple[str, str], Route],
) -> None:
    lanes = [(o, d) for o, d, _, _ in ref.LANES]
    lane_weights = [HEAVY_LANES.get(lane, 1) for lane in lanes]

    for index in range(ORDER_COUNT):
        scenario = SCENARIOS.get(index)
        lane = scenario.lane if scenario else rng.choices(lanes, lane_weights)[0]
        status = (
            scenario.status
            if scenario
            else rng.choices(STATUS_FLOW, [STATUS_WEIGHTS[s] for s in STATUS_FLOW])[0]
        )
        cold = scenario.cold if scenario else rng.random() < 0.25
        warehouse = warehouse_by_city[lane[0]]
        route = route_by_lane[lane]

        created_at = now - timedelta(hours=rng.uniform(*AGE_HOURS[status]))
        eta = _estimated_delivery(rng, now, status, route, created_at, scenario)

        order = Order(
            id=_uid(rng),
            order_number=f"ORD-{10001 + index}",
            customer_name=rng.choice(ref.CUSTOMERS),
            origin=lane[0],
            destination=lane[1],
            status=_order_status_for(status),
            priority=rng.choices(list(OrderPriority), [3, 10, 4, 1])[0],
            promised_delivery_at=eta + timedelta(hours=rng.uniform(0, 2)),
            created_at=created_at - timedelta(hours=rng.uniform(1, 6)),
            updated_at=created_at,
        )
        shipment = Shipment(
            id=_uid(rng),
            shipment_number=f"SHP-{2201 + index}",
            order_id=order.id,
            warehouse_id=warehouse.id,
            route_id=route.id,
            status=status,
            origin=lane[0],
            destination=lane[1],
            carrier=rng.choice(ref.CARRIERS),
            estimated_delivery=eta,
            temperature_status=TemperatureStatus.NORMAL
            if cold
            else TemperatureStatus.NOT_APPLICABLE,
            created_at=created_at,
            updated_at=now,
        )
        _assign_vehicle(rng, shipment, status, cold, data)
        events = _build_events(rng, now, shipment, status, cold, warehouse, scenario)
        if status == ShipmentStatus.DELIVERED:
            shipment.actual_delivery = events[-1].occurred_at
            shipment.estimated_delivery = min(eta, shipment.actual_delivery + timedelta(hours=1))
            order.promised_delivery_at = shipment.estimated_delivery + timedelta(hours=1)
        shipment.updated_at = events[-1].occurred_at

        data.orders.append(order)
        data.shipments.append(shipment)
        data.events.extend(events)
        data.exceptions.extend(_build_exceptions(rng, now, shipment, warehouse, events, scenario))


def _estimated_delivery(
    rng: random.Random,
    now: datetime,
    status: ShipmentStatus,
    route: Route,
    created_at: datetime,
    scenario: Scenario | None,
) -> datetime:
    """ETA relative to `now`: on time by default, already missed for deliberately late ones."""
    if status == ShipmentStatus.DELIVERED:
        prep = timedelta(hours=rng.uniform(2, 5))
        return created_at + prep + timedelta(minutes=route.estimated_duration_minutes)
    late_chance = 0.5 if route.status == RouteStatus.DELAYED else 0.06
    is_late = bool(scenario and scenario.late) or (
        status != ShipmentStatus.CREATED and rng.random() < late_chance
    )
    if is_late:
        return now - timedelta(hours=rng.uniform(0.4, 5))
    remaining = REMAINING_HOURS[status]
    return now + timedelta(hours=rng.uniform(*remaining))


def _order_status_for(status: ShipmentStatus) -> OrderStatus:
    if status == ShipmentStatus.DELIVERED:
        return OrderStatus.DELIVERED
    if status in (
        ShipmentStatus.IN_TRANSIT,
        ShipmentStatus.OUT_FOR_DELIVERY,
        ShipmentStatus.LOADED,
    ):
        return OrderStatus.SHIPPED
    return OrderStatus.PROCESSING


def _assign_vehicle(
    rng: random.Random,
    shipment: Shipment,
    status: ShipmentStatus,
    cold: bool,
    data: SeedData,
) -> None:
    if status in (ShipmentStatus.CREATED, ShipmentStatus.PICKED, ShipmentStatus.PACKED):
        return
    wanted = (
        {VehicleType.REFRIGERATED_TRUCK}
        if cold
        else set(VehicleType) - {VehicleType.REFRIGERATED_TRUCK}
    )
    candidates = [
        v for v in data.vehicles if v.vehicle_type in wanted and v.status != VehicleStatus.OFFLINE
        and (status == ShipmentStatus.DELIVERED or v.status != VehicleStatus.MAINTENANCE)
    ]  # fmt: skip
    home = [v for v in candidates if data.vehicle_home[v.id] == shipment.origin]
    vehicle = rng.choice(home or candidates)
    shipment.vehicle_id = vehicle.id
    if status != ShipmentStatus.DELIVERED:
        # Remember the leg so the vehicle can be positioned along its latest active shipment.
        vehicle.status = VehicleStatus.IN_TRANSIT
        data.vehicle_leg[vehicle.id] = shipment


def _build_events(
    rng: random.Random,
    now: datetime,
    shipment: Shipment,
    status: ShipmentStatus,
    cold: bool,
    warehouse: Warehouse,
    scenario: Scenario | None,
) -> list[TrackingEvent]:
    reached = STATUS_FLOW[: STATUS_FLOW.index(status) + 1]
    start = shipment.created_at
    if status == ShipmentStatus.DELIVERED:
        end = min(
            now - timedelta(minutes=30),
            shipment.estimated_delivery + timedelta(hours=rng.uniform(-1, 2)),
        )
    else:
        end = now - timedelta(minutes=rng.uniform(10, 40))
    step = (end - start) / max(len(reached) - 1, 1)

    events: list[TrackingEvent] = []
    for i, state in enumerate(reached):
        when = start + step * i if len(reached) > 1 else start
        at_warehouse = state in (
            ShipmentStatus.CREATED,
            ShipmentStatus.PICKED,
            ShipmentStatus.PACKED,
            ShipmentStatus.LOADED,
        )
        location = (
            warehouse.name
            if at_warehouse
            else (
                f"{shipment.destination} delivery depot"
                if state in (ShipmentStatus.OUT_FOR_DELIVERY, ShipmentStatus.DELIVERED)
                else f"A-road towards {shipment.destination}"
            )
        )
        details: dict[str, object] = {}
        if state == ShipmentStatus.CREATED:
            details["carrier"] = shipment.carrier
        if cold and state != ShipmentStatus.CREATED:
            details["temperature_c"] = round(rng.uniform(2.5, 6.0), 1)
        events.append(
            TrackingEvent(
                id=_uid(rng),
                shipment_id=shipment.id,
                event_type=EVENT_FOR_STATUS[state],
                location=location,
                occurred_at=when,
                details=details,
            )
        )
        if state == ShipmentStatus.IN_TRANSIT:
            events.append(_checkpoint(rng, shipment, when + step * 0.4, now))

    last = events[-1].occurred_at
    is_late = status != ShipmentStatus.DELIVERED and shipment.estimated_delivery < now
    if (scenario and scenario.transit_delay) or (
        is_late and status in (ShipmentStatus.IN_TRANSIT, ShipmentStatus.OUT_FOR_DELIVERY)
    ):
        minutes = 95 if scenario and scenario.transit_delay else rng.choice([40, 75, 120, 140])
        events.append(_delay_event(rng, shipment, last + timedelta(minutes=2), minutes))
    if scenario and scenario.deviation:
        shipment.temperature_status = TemperatureStatus.DEVIATION
        events.append(
            TrackingEvent(
                id=_uid(rng),
                shipment_id=shipment.id,
                event_type=TrackingEventType.TEMPERATURE_ALERT,
                location=f"A-road towards {shipment.destination}",
                occurred_at=last + timedelta(minutes=1),
                details={"temperature_c": 9.4, "allowed_range_c": [2.0, 8.0], "duration_min": 35},
            )
        )
    events.sort(key=lambda e: e.occurred_at)
    return events


def _checkpoint(
    rng: random.Random, shipment: Shipment, when: datetime, now: datetime
) -> TrackingEvent:
    return TrackingEvent(
        id=_uid(rng),
        shipment_id=shipment.id,
        event_type=TrackingEventType.CHECKPOINT,
        location=f"Checkpoint on route to {shipment.destination}",
        occurred_at=min(when, now - timedelta(minutes=2)),
        details={},
    )


def _delay_event(
    rng: random.Random, shipment: Shipment, after: datetime, minutes: int
) -> TrackingEvent:
    return TrackingEvent(
        id=_uid(rng),
        shipment_id=shipment.id,
        event_type=TrackingEventType.DELAY_REPORTED,
        location=f"A-road towards {shipment.destination}",
        occurred_at=after,
        details={"delay_minutes": minutes, "reason": "traffic congestion"},
    )


def _build_exceptions(
    rng: random.Random,
    now: datetime,
    shipment: Shipment,
    warehouse: Warehouse,
    events: list[TrackingEvent],
    scenario: Scenario | None,
) -> list[ShipmentException]:
    found: list[ShipmentException] = []

    def add(
        kind: ExceptionType,
        severity: ExceptionSeverity,
        text: str,
        resolution_note: str | None = None,
    ) -> None:
        resolved = resolution_note is not None
        raised_at = events[-1].occurred_at
        found.append(
            ShipmentException(
                id=_uid(rng),
                shipment_id=shipment.id,
                type=kind,
                severity=severity,
                description=text,
                status=ExceptionStatus.RESOLVED
                if resolved
                else rng.choice([ExceptionStatus.OPEN, ExceptionStatus.INVESTIGATING]),
                created_at=raised_at,
                resolved_at=raised_at + timedelta(hours=rng.uniform(1, 6)) if resolved else None,
                resolution_note=resolution_note,
            )
        )

    delivered = shipment.status == ShipmentStatus.DELIVERED
    late = not delivered and shipment.estimated_delivery < now
    hours_late = (now - shipment.estimated_delivery).total_seconds() / 3600
    if late:
        severity = ExceptionSeverity.HIGH if hours_late > 2 else ExceptionSeverity.MEDIUM
        add(
            ExceptionType.DELAYED,
            severity,
            f"Shipment to {shipment.destination} is {hours_late:.1f} h past its estimated delivery.",
        )
    if shipment.temperature_status == TemperatureStatus.DEVIATION:
        add(
            ExceptionType.TEMPERATURE_DEVIATION,
            ExceptionSeverity.CRITICAL,
            "Reefer unit reported 9.4 °C for 35 minutes; allowed range is 2-8 °C.",
        )
    if (
        warehouse.code == "WH-GAR"
        and shipment.status
        in (ShipmentStatus.CREATED, ShipmentStatus.PICKED, ShipmentStatus.PACKED)
        and rng.random() < 0.7
    ):
        add(
            ExceptionType.STOCK_SHORTAGE,
            ExceptionSeverity.HIGH,
            "Garbsen warehouse cannot fulfil all order lines: stock below reorder threshold.",
        )
    if delivered and rng.random() < 0.08:
        add(
            ExceptionType.DAMAGED,
            ExceptionSeverity.MEDIUM,
            "Damaged packaging reported on delivery; claim filed.",
            resolution_note="Customer accepted replacement; carrier claim filed.",
        )
    if not delivered and rng.random() < 0.04:
        add(
            ExceptionType.MISSING_DOCUMENT,
            ExceptionSeverity.LOW,
            "Delivery note missing from shipment paperwork.",
        )
    return found


def _build_backlog_orders(rng: random.Random, now: datetime, data: SeedData) -> None:
    lanes = [(o, d) for o, d, _, _ in ref.LANES]
    for i in range(BACKLOG_ORDER_COUNT):
        origin, destination = rng.choice(lanes)
        status = (
            OrderStatus.CANCELLED
            if i < 3
            else rng.choice([OrderStatus.PENDING, OrderStatus.CONFIRMED])
        )
        created = now - timedelta(hours=rng.uniform(0.2, 10))
        data.orders.append(
            Order(
                id=_uid(rng),
                order_number=f"ORD-{10001 + ORDER_COUNT + i}",
                customer_name=rng.choice(ref.CUSTOMERS),
                origin=origin,
                destination=destination,
                status=status,
                priority=rng.choice(list(OrderPriority)),
                promised_delivery_at=now + timedelta(hours=rng.uniform(12, 72)),
                created_at=created,
                updated_at=created,
            )
        )


def _update_vehicle_positions(
    rng: random.Random, data: SeedData, warehouse_by_city: dict[str, Warehouse]
) -> None:
    """Place vehicles that are on the road somewhere along their shipment's lane."""
    for vehicle in data.vehicles:
        shipment = data.vehicle_leg.get(vehicle.id)
        if shipment is None:
            continue
        origin = warehouse_by_city[shipment.origin]
        dest_lat, dest_lon = ref.CITIES[shipment.destination]
        progress = {
            ShipmentStatus.LOADED: 0.0,
            ShipmentStatus.IN_TRANSIT: rng.uniform(0.15, 0.85),
            ShipmentStatus.OUT_FOR_DELIVERY: rng.uniform(0.9, 1.0),
        }[shipment.status]
        vehicle.current_latitude = round(
            origin.latitude + (dest_lat - origin.latitude) * progress, 5
        )
        vehicle.current_longitude = round(
            origin.longitude + (dest_lon - origin.longitude) * progress, 5
        )
        vehicle.fuel_level = max(8.0, round(vehicle.fuel_level - progress * 20, 1))
