"""Data access for dock appointments and the scene's read model."""

import uuid
from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.modules.inventory.models import InventoryItem
from app.modules.orders.models import Order
from app.modules.shipments.models import Shipment, ShipmentStatus
from app.modules.warehouses.models import DockDirection, Warehouse
from app.modules.yard.models import DockAppointment
from app.modules.yard.rules import APPROACH_TIME, LEAVING_TIME
from app.modules.yard.simulator import PlannedVisit

# Shipments that are still at the warehouse: the ones a truck can plausibly be loading.
LOADABLE = (
    ShipmentStatus.CREATED,
    ShipmentStatus.PICKED,
    ShipmentStatus.PACKED,
    ShipmentStatus.LOADED,
)


class YardRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def lock_warehouse(self, warehouse_id: uuid.UUID) -> None:
        """Serialise schedule top-ups for one site (two requests must not plan the same visit)."""
        await self.session.execute(
            select(Warehouse.id).where(Warehouse.id == warehouse_id).with_for_update()
        )

    async def last_visit_per_dock(
        self, warehouse_id: uuid.UUID
    ) -> dict[uuid.UUID, tuple[int, datetime]]:
        """dock_id -> (highest sequence, when that visit departs)."""
        rows = await self.session.execute(
            select(
                DockAppointment.dock_id,
                func.max(DockAppointment.sequence),
                func.max(DockAppointment.departs_at),
            )
            .where(DockAppointment.warehouse_id == warehouse_id)
            .group_by(DockAppointment.dock_id)
        )
        return {dock_id: (sequence, departs_at) for dock_id, sequence, departs_at in rows}

    async def loadable_shipments(self, warehouse_id: uuid.UUID) -> Sequence[Shipment]:
        result = await self.session.scalars(
            select(Shipment)
            .where(Shipment.warehouse_id == warehouse_id, Shipment.status.in_(LOADABLE))
            .order_by(Shipment.shipment_number)
        )
        return result.all()

    def add_visit(
        self,
        warehouse: Warehouse,
        dock_id: uuid.UUID,
        direction: DockDirection,
        planned: PlannedVisit,
        shipment_id: uuid.UUID | None,
    ) -> None:
        self.session.add(
            DockAppointment(
                warehouse_id=warehouse.id,
                dock_id=dock_id,
                shipment_id=shipment_id,
                direction=direction,
                sequence=planned.sequence,
                truck_code=planned.truck_code,
                carrier=planned.carrier,
                pallets_total=planned.pallets_total,
                arrives_at=planned.arrives_at,
                docked_at=planned.docked_at,
                departs_at=planned.departs_at,
            )
        )

    async def prune_before(self, warehouse_id: uuid.UUID, cutoff: datetime) -> None:
        await self.session.execute(
            delete(DockAppointment).where(
                DockAppointment.warehouse_id == warehouse_id, DockAppointment.departs_at < cutoff
            )
        )

    async def visible_visits(
        self, warehouse_id: uuid.UUID, now: datetime
    ) -> Sequence[DockAppointment]:
        """Visits whose truck could be on screen now (state is derived afterwards)."""
        result = await self.session.scalars(
            select(DockAppointment)
            .where(
                DockAppointment.warehouse_id == warehouse_id,
                DockAppointment.arrives_at - APPROACH_TIME <= now,
                DockAppointment.departs_at + LEAVING_TIME > now,
            )
            .options(joinedload(DockAppointment.dock), joinedload(DockAppointment.shipment))
            .order_by(DockAppointment.arrives_at)
        )
        return result.all()

    async def trucks_today_by_dock(
        self, warehouse_id: uuid.UUID, start: datetime, end: datetime, now: datetime
    ) -> dict[uuid.UUID, int]:
        """Trucks that have arrived at each dock so far in [start, end)."""
        rows = await self.session.execute(
            select(DockAppointment.dock_id, func.count())
            .where(
                DockAppointment.warehouse_id == warehouse_id,
                DockAppointment.arrives_at >= start,
                DockAppointment.arrives_at < end,
                DockAppointment.arrives_at <= now,
            )
            .group_by(DockAppointment.dock_id)
        )
        return {row[0]: row[1] for row in rows}

    async def inventory(self, warehouse_id: uuid.UUID) -> Sequence[InventoryItem]:
        result = await self.session.scalars(
            select(InventoryItem)
            .where(InventoryItem.warehouse_id == warehouse_id)
            .order_by(InventoryItem.sku)
        )
        return result.all()

    async def deliveries(
        self, warehouse_id: uuid.UUID, start: datetime, end: datetime
    ) -> tuple[int, int]:
        """(delivered, on time) for this site's deliveries in [start, end), against the
        promise made to the customer."""
        delivered, on_time = (
            await self.session.execute(
                select(
                    func.count(),
                    func.count().filter(Shipment.actual_delivery <= Order.promised_delivery_at),
                )
                .select_from(Shipment)
                .join(Order, Order.id == Shipment.order_id)
                .where(
                    Shipment.warehouse_id == warehouse_id,
                    Shipment.status == ShipmentStatus.DELIVERED,
                    Shipment.actual_delivery >= start,
                    Shipment.actual_delivery < end,
                )
            )
        ).one()
        return delivered, on_time
