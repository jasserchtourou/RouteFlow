"""Use cases for the yard: keep the simulated schedule topped up and build the scene payload."""

import uuid
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import business_day
from app.core.errors import NotFoundError
from app.modules.inventory.rules import StockStatus
from app.modules.warehouses.models import Dock, DockDirection, DockStatus, Equipment, Warehouse
from app.modules.warehouses.repository import WarehouseRepository
from app.modules.yard import rules
from app.modules.yard.models import DockAppointment
from app.modules.yard.repository import YardRepository
from app.modules.yard.rules import VisitState
from app.modules.yard.schemas import (
    SceneDock,
    SceneEquipment,
    SceneKpis,
    SceneLayout,
    ScenePallet,
    SceneRead,
    SceneShipment,
    SceneTimings,
    SceneVisit,
    SceneWarehouse,
)
from app.modules.yard.simulator import FIRST_VISIT_OFFSET, HORIZON, RETENTION, plan_until

MAX_SCENE_PALLETS = 48
MIN_YARD_SLOTS = 4
KPI_WINDOW = timedelta(days=30)
FIRST_PALLET_NUMBER = 1001


class YardService:
    def __init__(
        self, session: AsyncSession, timezone: str, *, simulation_enabled: bool = True
    ) -> None:
        self.session = session
        self.timezone = timezone
        self.simulation_enabled = simulation_enabled
        self.warehouses = WarehouseRepository(session)
        self.yard = YardRepository(session)

    # --- simulator -----------------------------------------------------------------------

    async def top_up_schedule(self, warehouse: Warehouse, docks: list[Dock], now: datetime) -> int:
        """Plan visits for every working dock until the schedule reaches HORIZON. Returns how
        many were added. Idempotent: a second call at the same time adds nothing."""
        await self.yard.lock_warehouse(warehouse.id)
        last = await self.yard.last_visit_per_dock(warehouse.id)
        shipments = list(await self.yard.loadable_shipments(warehouse.id))
        added = 0
        for dock in docks:
            if dock.status != DockStatus.AVAILABLE:
                continue
            sequence, free_from = last.get(dock.id, (-1, now - FIRST_VISIT_OFFSET))
            planned = plan_until(warehouse.code, dock.code, sequence + 1, free_from, now + HORIZON)
            for visit in planned:
                # Outbound trucks carry a shipment that is still waiting at this warehouse.
                shipment_id = None
                if dock.direction == DockDirection.OUTBOUND and shipments:
                    shipment_id = shipments[(dock.position + visit.sequence) % len(shipments)].id
                self.yard.add_visit(warehouse, dock.id, dock.direction, visit, shipment_id)
            added += len(planned)
        await self.yard.prune_before(warehouse.id, now - RETENTION)
        if added:
            await self.session.commit()
        return added

    # --- scene -----------------------------------------------------------------------------

    async def scene(self, warehouse_id: uuid.UUID, now: datetime) -> SceneRead:
        warehouse = await self.warehouses.get(warehouse_id)
        if warehouse is None:
            raise NotFoundError(
                f"Warehouse {warehouse_id} not found", details={"id": str(warehouse_id)}
            )
        docks = list(await self.warehouses.docks(warehouse.id))
        equipment = list(await self.warehouses.equipment(warehouse.id))
        if self.simulation_enabled:
            await self.top_up_schedule(warehouse, docks, now)

        appointments = await self.yard.visible_visits(warehouse.id, now)
        visits = [self._visit(a, now) for a in appointments]
        today = business_day(now, self.timezone)
        trucks_today = await self.yard.trucks_today_by_dock(
            warehouse.id, today.start, today.end, now
        )

        return SceneRead(
            generated_at=now,
            warehouse=SceneWarehouse(
                id=warehouse.id,
                code=warehouse.code,
                name=warehouse.name,
                location=warehouse.location,
                status=warehouse.status,
                capacity=warehouse.capacity,
                stock_pallets=warehouse.current_utilization,
                utilization_pct=round(warehouse.utilization_pct, 1),
            ),
            kpis=await self._kpis(warehouse, docks, visits, now),
            layout=SceneLayout(dock_count=len(docks), yard_slots=max(MIN_YARD_SLOTS, len(docks))),
            timings=SceneTimings(
                approach_seconds=int(rules.APPROACH_TIME.total_seconds()),
                docking_seconds=int(rules.DOCKING_TIME.total_seconds()),
                leaving_seconds=int(rules.LEAVING_TIME.total_seconds()),
            ),
            docks=self._docks(docks, visits, trucks_today),
            visits=[v for v in visits if v.state in rules.VISIBLE_STATES],
            equipment=self._equipment(equipment, visits),
            pallets=await self._pallets(warehouse.id),
        )

    # --- builders ----------------------------------------------------------------------------

    @staticmethod
    def _visit(appointment: DockAppointment, now: datetime) -> SceneVisit:
        state = rules.visit_state(
            appointment.arrives_at,
            appointment.docked_at,
            appointment.departs_at,
            appointment.direction,
            now,
        )
        shipment = appointment.shipment
        return SceneVisit(
            id=appointment.id,
            truck_code=appointment.truck_code,
            carrier=appointment.carrier,
            direction=appointment.direction,
            dock_code=appointment.dock.code,
            state=state,
            arrives_at=appointment.arrives_at,
            docked_at=appointment.docked_at,
            departs_at=appointment.departs_at,
            pallets_total=appointment.pallets_total,
            pallets_done=rules.pallets_done(
                appointment.docked_at, appointment.departs_at, appointment.pallets_total, now
            ),
            minutes_remaining=rules.minutes_remaining(
                state, appointment.docked_at, appointment.departs_at, now
            ),
            shipment=None
            if shipment is None
            else SceneShipment(
                shipment_number=shipment.shipment_number,
                destination=shipment.destination,
                status=shipment.status,
                estimated_delivery=shipment.estimated_delivery,
            ),
        )

    @staticmethod
    def _docks(
        docks: list[Dock], visits: list[SceneVisit], trucks_today: dict[uuid.UUID, int]
    ) -> list[SceneDock]:
        by_dock: dict[str, list[SceneVisit]] = {}
        for visit in visits:
            by_dock.setdefault(visit.dock_code, []).append(visit)
        result = []
        for dock in docks:
            dock_visits = by_dock.get(dock.code, [])
            current = next(
                (v for v in dock_visits if v.state in rules.AT_DOOR_STATES),
                next(
                    (
                        v
                        for v in dock_visits
                        if v.state in {VisitState.EN_ROUTE, VisitState.WAITING}
                    ),
                    None,
                ),
            )
            result.append(
                SceneDock(
                    id=dock.id,
                    code=dock.code,
                    direction=dock.direction,
                    position=dock.position,
                    state=rules.dock_state(dock.status, (v.state for v in dock_visits)),
                    visit_id=current.id if current else None,
                    trucks_today=trucks_today.get(dock.id, 0),
                )
            )
        return result

    @staticmethod
    def _equipment(equipment: list[Equipment], visits: list[SceneVisit]) -> list[SceneEquipment]:
        working_docks = sorted({v.dock_code for v in visits if v.state in rules.WORKING_STATES})
        assigned = rules.assign_equipment([(e.code, e.status) for e in equipment], working_docks)
        return [
            SceneEquipment(
                id=e.id,
                code=e.code,
                equipment_type=e.equipment_type,
                status=e.status,
                battery_level=e.battery_level,
                assigned_dock_code=assigned.get(e.code),
            )
            for e in equipment
        ]

    async def _pallets(self, warehouse_id: uuid.UUID) -> list[ScenePallet]:
        items = list(await self.yard.inventory(warehouse_id))[:MAX_SCENE_PALLETS]
        return [
            ScenePallet(
                id=f"PAL-{FIRST_PALLET_NUMBER + index}",
                sku=item.sku,
                product_name=item.product_name,
                quantity=item.quantity,
                slot=index,
                stock_status=item.stock_status,
                has_issue=item.stock_status != StockStatus.OK,
            )
            for index, item in enumerate(items)
        ]

    async def _kpis(
        self, warehouse: Warehouse, docks: list[Dock], visits: list[SceneVisit], now: datetime
    ) -> SceneKpis:
        on_site = [v for v in visits if v.state in rules.ON_SITE_STATES]
        recent = await self.yard.deliveries(warehouse.id, now - KPI_WINDOW, now)
        previous = await self.yard.deliveries(warehouse.id, now - 2 * KPI_WINDOW, now - KPI_WINDOW)
        rate = _rate(*recent)
        before = _rate(*previous)
        return SceneKpis(
            stock_on_hand_pallets=warehouse.current_utilization,
            trucks_on_site=len(on_site),
            inbound_trucks_on_site=sum(1 for v in on_site if v.direction == DockDirection.INBOUND),
            docks_occupied=sum(1 for v in on_site if v.state in rules.AT_DOOR_STATES),
            docks_total=len(docks),
            on_time_rate_30d=rate,
            on_time_change_pts=None if rate is None or before is None else round(rate - before, 1),
        )


def _rate(delivered: int, on_time: int) -> float | None:
    return None if delivered == 0 else round(on_time * 100.0 / delivered, 1)
