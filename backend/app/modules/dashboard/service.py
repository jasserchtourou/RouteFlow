"""Operations dashboard: one call that summarises the whole network."""

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import DayWindow, business_day
from app.modules.dashboard import rules
from app.modules.dashboard.repository import DashboardRepository
from app.modules.dashboard.schemas import (
    DashboardOverview,
    DeliveryPerformance,
    DeliveryWindow,
    ExceptionStats,
    OrderStats,
    ShipmentStats,
    WarehouseStats,
)
from app.modules.exceptions.models import ExceptionSeverity
from app.modules.orders.models import OrderStatus
from app.modules.shipments.models import ShipmentStatus
from app.modules.vehicles.service import VehicleService
from app.modules.warehouses.rules import UtilizationLevel
from app.modules.warehouses.schemas import WarehouseListParams
from app.modules.warehouses.service import WarehouseService

CLOSED_ORDER_STATUSES = (OrderStatus.DELIVERED, OrderStatus.CANCELLED)
ON_THE_ROAD = (ShipmentStatus.IN_TRANSIT, ShipmentStatus.OUT_FOR_DELIVERY)


class DashboardService:
    def __init__(self, session: AsyncSession, timezone: str) -> None:
        self.timezone = timezone
        self.stats = DashboardRepository(session)
        self.fleet = VehicleService(session)
        self.warehouses = WarehouseService(session)

    async def overview(self, now: datetime) -> DashboardOverview:
        today = business_day(now, self.timezone)
        return DashboardOverview(
            generated_at=now,
            timezone=self.timezone,
            orders=await self._orders(today),
            shipments=await self._shipments(now, today),
            exceptions=await self._exceptions(),
            fleet=await self.fleet.overview(),
            warehouses=await self._warehouses(),
            delivery_performance=await self._delivery_performance(now),
        )

    async def _orders(self, today: DayWindow) -> OrderStats:
        by_status = await self.stats.orders_by_status()
        return OrderStats(
            total=sum(by_status.values()),
            open=sum(n for s, n in by_status.items() if s not in CLOSED_ORDER_STATUSES),
            created_today=await self.stats.orders_created_in(today),
            by_status=by_status,
        )

    async def _shipments(self, now: datetime, today: DayWindow) -> ShipmentStats:
        by_status = await self.stats.shipments_by_status()
        delivered_today, _ = await self.stats.deliveries(today.start, today.end)
        return ShipmentStats(
            total=sum(by_status.values()),
            active=sum(n for s, n in by_status.items() if s != ShipmentStatus.DELIVERED),
            in_transit=sum(by_status[s] for s in ON_THE_ROAD),
            delayed=await self.stats.delayed_shipments(now),
            delivered_today=delivered_today,
            by_status=by_status,
        )

    async def _exceptions(self) -> ExceptionStats:
        by_severity = await self.stats.active_exceptions_by_severity()
        return ExceptionStats(
            active=sum(by_severity.values()),
            critical=by_severity[ExceptionSeverity.CRITICAL],
            by_severity=by_severity,
            by_type=await self.stats.active_exceptions_by_type(),
        )

    async def _warehouses(self) -> WarehouseStats:
        page = await self.warehouses.list(WarehouseListParams(limit=100))
        capacity = sum(w.capacity for w in page.items)
        used = sum(w.current_utilization for w in page.items)
        return WarehouseStats(
            count=page.total,
            network_utilization_pct=round(used * 100.0 / capacity, 1) if capacity else None,
            critical_utilization=sum(
                1 for w in page.items if w.utilization_level == UtilizationLevel.CRITICAL
            ),
            items=page.items,
        )

    async def _delivery_performance(self, now: datetime) -> DeliveryPerformance:
        today = business_day(now, self.timezone)
        yesterday = business_day(now, self.timezone, days_ago=1)
        week_start = business_day(now, self.timezone, days_ago=6).start
        windows = {
            "today": await self._window(today.start, today.end),
            "yesterday": await self._window(yesterday.start, yesterday.end),
            "last_7_days": await self._window(week_start, today.end),
        }
        return DeliveryPerformance(
            **windows,
            change_vs_yesterday_pts=rules.change_in_points(
                windows["today"].on_time_rate, windows["yesterday"].on_time_rate
            ),
        )

    async def _window(self, start: datetime, end: datetime) -> DeliveryWindow:
        delivered, on_time = await self.stats.deliveries(start, end)
        return DeliveryWindow(
            delivered=delivered,
            on_time=on_time,
            on_time_rate=rules.on_time_rate(on_time, delivered),
        )
