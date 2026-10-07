"""Data access for drivers."""

import uuid
from collections.abc import Sequence

from sqlalchemy import Row, Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.querying import contains_any, paginate_rows
from app.modules.drivers.models import Driver
from app.modules.drivers.schemas import DriverListParams
from app.modules.vehicles.models import Vehicle

DriverRow = Row[Driver, uuid.UUID | None, str | None]
DriverQuery = Select[Driver, uuid.UUID | None, str | None]


def _with_vehicle() -> DriverQuery:
    query: DriverQuery = select(Driver, Vehicle.id, Vehicle.registration).outerjoin(
        Vehicle, Vehicle.driver_id == Driver.id
    )
    return query


class DriverRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_row(self, driver_id: uuid.UUID) -> DriverRow | None:
        result = await self.session.execute(_with_vehicle().where(Driver.id == driver_id))
        return result.one_or_none()

    async def list(self, params: DriverListParams) -> tuple[Sequence[DriverRow], int]:
        query = _with_vehicle()
        if params.status:
            query = query.where(Driver.status.in_(params.status))
        if params.search:
            query = query.where(
                contains_any(params.search, Driver.full_name, Driver.license_number)
            )
        query = query.order_by(Driver.full_name, Driver.id)
        return await paginate_rows(self.session, query, params)
