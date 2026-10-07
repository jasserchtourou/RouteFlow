"""Tiny builders for valid model instances; tests override only what they care about."""

from datetime import UTC, datetime, timedelta
from itertools import count
from typing import Any

from app.modules.inventory.models import InventoryItem
from app.modules.orders.models import Order
from app.modules.routes.models import Route
from app.modules.shipments.models import Shipment, ShipmentStatus
from app.modules.vehicles.models import Vehicle, VehicleType
from app.modules.warehouses.models import (
    Dock,
    DockDirection,
    Equipment,
    EquipmentType,
    Warehouse,
)

_counter = count(1)


def _n() -> int:
    return next(_counter)


def make_warehouse(**overrides: Any) -> Warehouse:
    n = _n()
    values: dict[str, Any] = {
        "code": f"WH-T{n:03d}",
        "name": f"Test Warehouse {n}",
        "location": "Hannover",
        "latitude": 52.37,
        "longitude": 9.73,
        "capacity": 1000,
        "current_utilization": 500,
    }
    return Warehouse(**{**values, **overrides})


def make_order(**overrides: Any) -> Order:
    n = _n()
    values: dict[str, Any] = {
        "order_number": f"ORD-T{n:05d}",
        "customer_name": "Test GmbH",
        "origin": "Hannover",
        "destination": "Hamburg",
        "promised_delivery_at": datetime.now(UTC) + timedelta(days=1),
    }
    return Order(**{**values, **overrides})


def make_route(**overrides: Any) -> Route:
    n = _n()
    values: dict[str, Any] = {
        "route_number": f"RTE-T{n:03d}",
        "origin": "Hannover",
        "destination": "Hamburg",
        "distance_km": 155.0,
        "estimated_duration_minutes": 120,
    }
    return Route(**{**values, **overrides})


def make_vehicle(**overrides: Any) -> Vehicle:
    n = _n()
    values: dict[str, Any] = {
        "registration": f"H-T {n:04d}",
        "vehicle_type": VehicleType.VAN,
        "fuel_level": 80.0,
    }
    return Vehicle(**{**values, **overrides})


def make_inventory_item(warehouse: Warehouse, **overrides: Any) -> InventoryItem:
    n = _n()
    values: dict[str, Any] = {
        "warehouse_id": warehouse.id,
        "sku": f"SKU-{n:04d}",
        "product_name": "Test Product",
        "quantity": 100,
        "reserved_quantity": 10,
        "reorder_threshold": 20,
    }
    return InventoryItem(**{**values, **overrides})


def make_shipment(order: Order, warehouse: Warehouse, **overrides: Any) -> Shipment:
    n = _n()
    values: dict[str, Any] = {
        "shipment_number": f"SHP-T{n:05d}",
        "order_id": order.id,
        "warehouse_id": warehouse.id,
        "status": ShipmentStatus.CREATED,
        "origin": "Hannover",
        "destination": "Hamburg",
        "carrier": "Test Carrier",
        "estimated_delivery": datetime.now(UTC) + timedelta(hours=8),
    }
    return Shipment(**{**values, **overrides})


def make_dock(warehouse: Warehouse, **overrides: Any) -> Dock:
    n = _n()
    values: dict[str, Any] = {
        "warehouse_id": warehouse.id,
        "code": f"In {n}",
        "direction": DockDirection.INBOUND,
        "position": n,
    }
    return Dock(**{**values, **overrides})


def make_equipment(warehouse: Warehouse, **overrides: Any) -> Equipment:
    n = _n()
    values: dict[str, Any] = {
        "warehouse_id": warehouse.id,
        "code": f"FL-{n:03d}",
        "equipment_type": EquipmentType.FORKLIFT,
        "battery_level": 75.0,
    }
    return Equipment(**{**values, **overrides})
