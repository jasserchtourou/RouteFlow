"""Vehicle and fleet use cases."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.core.pagination import Page
from app.modules.vehicles import rules
from app.modules.vehicles.models import VehicleStatus
from app.modules.vehicles.repository import VehicleRepository, VehicleRow
from app.modules.vehicles.schemas import FleetOverview, Position, VehicleListParams, VehicleRead


def to_read(row: VehicleRow) -> VehicleRead:
    vehicle, driver_name, on_board = row
    lat, lon = vehicle.current_latitude, vehicle.current_longitude
    return VehicleRead(
        id=vehicle.id,
        registration=vehicle.registration,
        vehicle_type=vehicle.vehicle_type,
        status=vehicle.status,
        fuel_level=vehicle.fuel_level,
        low_fuel=rules.is_low_fuel(vehicle.fuel_level),
        position=Position(latitude=lat, longitude=lon)
        if lat is not None and lon is not None
        else None,
        driver_id=vehicle.driver_id,
        driver_name=driver_name,
        active_shipments=on_board or [],
        updated_at=vehicle.updated_at,
    )


class VehicleService:
    def __init__(self, session: AsyncSession) -> None:
        self.vehicles = VehicleRepository(session)

    async def list(self, params: VehicleListParams) -> Page[VehicleRead]:
        rows, total = await self.vehicles.list(params)
        return Page[VehicleRead](
            items=[to_read(row) for row in rows],
            total=total,
            limit=params.limit,
            offset=params.offset,
        )

    async def get(self, vehicle_id: uuid.UUID) -> VehicleRead:
        row = await self.vehicles.get_row(vehicle_id)
        if row is None:
            raise NotFoundError(f"Vehicle {vehicle_id} not found", details={"id": str(vehicle_id)})
        return to_read(row)

    async def get_by_registration(self, registration: str) -> VehicleRead:
        row = await self.vehicles.get_row_by_registration(registration)
        if row is None:
            raise NotFoundError(
                f"Vehicle {registration} not found", details={"registration": registration}
            )
        return to_read(row)

    async def overview(self) -> FleetOverview:
        by_status = await self.vehicles.count_by_status()
        operational = sum(by_status[s] for s in rules.OPERATIONAL_STATUSES)
        return FleetOverview(
            total=sum(by_status.values()),
            by_status=by_status,
            by_type=await self.vehicles.count_by_type(),
            operational=operational,
            utilization_pct=rules.fleet_utilization_pct(
                by_status[VehicleStatus.IN_TRANSIT], operational
            ),
            low_fuel=await self.vehicles.count_low_fuel(),
            drivers_by_status=await self.vehicles.drivers_by_status(),
        )
