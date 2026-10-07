from datetime import datetime

from pydantic import BaseModel, Field

from app.modules.exceptions.models import ExceptionSeverity, ExceptionType
from app.modules.orders.models import OrderStatus
from app.modules.shipments.models import ShipmentStatus
from app.modules.vehicles.schemas import FleetOverview
from app.modules.warehouses.schemas import WarehouseListItem


class OrderStats(BaseModel):
    total: int
    open: int = Field(description="Not delivered and not cancelled")
    created_today: int
    by_status: dict[OrderStatus, int]


class ShipmentStats(BaseModel):
    total: int
    active: int = Field(description="Not yet delivered")
    in_transit: int = Field(description="IN_TRANSIT + OUT_FOR_DELIVERY")
    delayed: int
    delivered_today: int
    by_status: dict[ShipmentStatus, int]


class ExceptionStats(BaseModel):
    active: int
    critical: int
    by_severity: dict[ExceptionSeverity, int]
    by_type: dict[ExceptionType, int]


class WarehouseStats(BaseModel):
    count: int
    network_utilization_pct: float | None = Field(
        description="Occupied / total pallet positions across all sites (capacity-weighted)"
    )
    critical_utilization: int
    items: list[WarehouseListItem]


class DeliveryWindow(BaseModel):
    delivered: int
    on_time: int
    on_time_rate: float | None = Field(description="% delivered by the promised time")


class DeliveryPerformance(BaseModel):
    today: DeliveryWindow
    yesterday: DeliveryWindow
    last_7_days: DeliveryWindow
    change_vs_yesterday_pts: float | None = Field(
        description="Today's on-time rate minus yesterday's, in percentage points"
    )


class DashboardOverview(BaseModel):
    generated_at: datetime
    timezone: str
    orders: OrderStats
    shipments: ShipmentStats
    exceptions: ExceptionStats
    fleet: FleetOverview
    warehouses: WarehouseStats
    delivery_performance: DeliveryPerformance
