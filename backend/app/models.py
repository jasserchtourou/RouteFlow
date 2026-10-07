"""Model registry.

Importing this module registers every table on Base.metadata. Alembic, the seed script and
the tests import it so that relationships (which refer to each other by name) can resolve.
"""

from app.modules.documents.models import Document
from app.modules.drivers.models import Driver
from app.modules.exceptions.models import ShipmentException
from app.modules.inventory.models import InventoryItem
from app.modules.orders.models import Order
from app.modules.routes.models import Route
from app.modules.shipments.models import Shipment
from app.modules.tracking.models import TrackingEvent
from app.modules.vehicles.models import Vehicle
from app.modules.warehouses.models import Dock, Equipment, Warehouse
from app.modules.yard.models import DockAppointment

__all__ = [
    "Dock",
    "DockAppointment",
    "Document",
    "Driver",
    "Equipment",
    "InventoryItem",
    "Order",
    "Route",
    "Shipment",
    "ShipmentException",
    "TrackingEvent",
    "Vehicle",
    "Warehouse",
]
