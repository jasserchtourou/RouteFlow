"""Driver use cases."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.core.pagination import Page
from app.modules.drivers.repository import DriverRepository, DriverRow
from app.modules.drivers.schemas import DriverListParams, DriverRead


def to_read(row: DriverRow) -> DriverRead:
    driver, vehicle_id, registration = row
    return DriverRead(
        id=driver.id,
        full_name=driver.full_name,
        license_number=driver.license_number,
        phone=driver.phone,
        status=driver.status,
        vehicle_id=vehicle_id,
        vehicle_registration=registration,
    )


class DriverService:
    def __init__(self, session: AsyncSession) -> None:
        self.drivers = DriverRepository(session)

    async def list(self, params: DriverListParams) -> Page[DriverRead]:
        rows, total = await self.drivers.list(params)
        return Page[DriverRead](
            items=[to_read(row) for row in rows],
            total=total,
            limit=params.limit,
            offset=params.offset,
        )

    async def get(self, driver_id: uuid.UUID) -> DriverRead:
        row = await self.drivers.get_row(driver_id)
        if row is None:
            raise NotFoundError(f"Driver {driver_id} not found", details={"id": str(driver_id)})
        return to_read(row)
