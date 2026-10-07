"""Data access for vehicles and fleet aggregates."""

import uuid
from collections.abc import Sequence

from sqlalchemy import Row, Select, func, select
from sqlalchemy.dialects.postgresql import aggregate_order_by
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.querying import Column, apply_sort, contains_any, paginate_rows
from app.modules.drivers.models import Driver, DriverStatus
from app.modules.shipments.models import Shipment, ShipmentStatus
from app.modules.vehicles.models import Vehicle, VehicleStatus, VehicleType
from app.modules.vehicles.rules import LOW_FUEL_PCT
from app.modules.vehicles.schemas import VehicleListParams

VehicleRow = Row[Vehicle, str | None, list[str] | None]
VehicleQuery = Select[Vehicle, str | None, list[str] | None]

ON_BOARD = (ShipmentStatus.LOADED, ShipmentStatus.IN_TRANSIT, ShipmentStatus.OUT_FOR_DELIVERY)

_on_board = (
    select(
        Shipment.vehicle_id,
        func.array_agg(
            aggregate_order_by(Shipment.shipment_number, Shipment.estimated_delivery)
        ).label("numbers"),
    )
    .where(Shipment.status.in_(ON_BOARD), Shipment.vehicle_id.is_not(None))
    .group_by(Shipment.vehicle_id)
    .subquery()
)

_SORT_COLUMNS: dict[str, Column] = {
    "registration": Vehicle.registration,
    "fuel": Vehicle.fuel_level,
}


def _with_context() -> VehicleQuery:
    query: VehicleQuery = (
        select(Vehicle, Driver.full_name, _on_board.c.numbers)
        .outerjoin(Driver, Driver.id == Vehicle.driver_id)
        .outerjoin(_on_board, _on_board.c.vehicle_id == Vehicle.id)
    )
    return query


class VehicleRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_row(self, vehicle_id: uuid.UUID) -> VehicleRow | None:
        result = await self.session.execute(_with_context().where(Vehicle.id == vehicle_id))
        return result.one_or_none()

    async def get_row_by_registration(self, registration: str) -> VehicleRow | None:
        result = await self.session.execute(
            _with_context().where(Vehicle.registration == registration.upper())
        )
        return result.one_or_none()

    async def list(self, params: VehicleListParams) -> tuple[Sequence[VehicleRow], int]:
        query = _with_context()
        if params.status:
            query = query.where(Vehicle.status.in_(params.status))
        if params.vehicle_type:
            query = query.where(Vehicle.vehicle_type.in_(params.vehicle_type))
        if params.low_fuel is not None:
            low = Vehicle.fuel_level < LOW_FUEL_PCT
            query = query.where(low if params.low_fuel else ~low)
        if params.search:
            query = query.where(contains_any(params.search, Vehicle.registration))
        query = apply_sort(query, params.sort.value, _SORT_COLUMNS, tiebreaker=Vehicle.id)
        return await paginate_rows(self.session, query, params)

    async def count_by_status(self) -> dict[VehicleStatus, int]:
        rows = await self.session.execute(
            select(Vehicle.status, func.count()).group_by(Vehicle.status)
        )
        return dict.fromkeys(VehicleStatus, 0) | dict(rows.all())

    async def count_by_type(self) -> dict[VehicleType, int]:
        rows = await self.session.execute(
            select(Vehicle.vehicle_type, func.count()).group_by(Vehicle.vehicle_type)
        )
        return dict.fromkeys(VehicleType, 0) | dict(rows.all())

    async def count_low_fuel(self) -> int:
        count = await self.session.scalar(
            select(func.count()).where(Vehicle.fuel_level < LOW_FUEL_PCT)
        )
        return count or 0

    async def drivers_by_status(self) -> dict[DriverStatus, int]:
        rows = await self.session.execute(
            select(Driver.status, func.count()).group_by(Driver.status)
        )
        return dict.fromkeys(DriverStatus, 0) | dict(rows.all())
