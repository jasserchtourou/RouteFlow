"""Shipment read use cases (state changes arrive as tracking events, see tracking/service.py)."""

import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.core.pagination import Page
from app.modules.exceptions.schemas import ExceptionCreate, ExceptionRead
from app.modules.exceptions.service import ExceptionService
from app.modules.shipments import rules
from app.modules.shipments.models import Shipment
from app.modules.shipments.repository import ShipmentRepository, ShipmentRow
from app.modules.shipments.schemas import ShipmentDetail, ShipmentListParams, ShipmentRead
from app.modules.tracking.repository import TrackingRepository
from app.modules.tracking.schemas import TrackingEventRead


def to_read(row: ShipmentRow, now: datetime) -> ShipmentRead:
    shipment, order_number, warehouse_code, route_number, registration, active = row
    return ShipmentRead(
        id=shipment.id,
        shipment_number=shipment.shipment_number,
        status=shipment.status,
        order_id=shipment.order_id,
        order_number=order_number,
        warehouse_id=shipment.warehouse_id,
        warehouse_code=warehouse_code,
        route_id=shipment.route_id,
        route_number=route_number,
        vehicle_id=shipment.vehicle_id,
        vehicle_registration=registration,
        origin=shipment.origin,
        destination=shipment.destination,
        carrier=shipment.carrier,
        estimated_delivery=shipment.estimated_delivery,
        actual_delivery=shipment.actual_delivery,
        temperature_status=shipment.temperature_status,
        is_delayed=rules.is_delayed(shipment.status, shipment.estimated_delivery, now),
        delay_minutes=rules.delay_minutes(
            shipment.status, shipment.estimated_delivery, shipment.actual_delivery, now
        ),
        active_exception_count=active,
        created_at=shipment.created_at,
        updated_at=shipment.updated_at,
    )


class ShipmentService:
    def __init__(self, session: AsyncSession) -> None:
        self.shipments = ShipmentRepository(session)
        self.events = TrackingRepository(session)
        self.exceptions = ExceptionService(session)

    async def list(self, params: ShipmentListParams) -> Page[ShipmentRead]:
        now = datetime.now(UTC)  # one reference time for the SQL filter and the flags
        rows, total = await self.shipments.list(params, now)
        return Page[ShipmentRead](
            items=[to_read(row, now) for row in rows],
            total=total,
            limit=params.limit,
            offset=params.offset,
        )

    async def get(self, shipment_id: uuid.UUID) -> Shipment:
        shipment = await self.shipments.get(shipment_id)
        if shipment is None:
            raise _not_found(shipment_id)
        return shipment

    async def lock(self, shipment_id: uuid.UUID) -> Shipment:
        shipment = await self.shipments.get_for_update(shipment_id)
        if shipment is None:
            raise _not_found(shipment_id)
        return shipment

    async def read(self, shipment_id: uuid.UUID) -> ShipmentRead:
        row = await self.shipments.get_row(shipment_id)
        if row is None:
            raise _not_found(shipment_id)
        return to_read(row, datetime.now(UTC))

    async def detail(self, shipment_id: uuid.UUID) -> ShipmentDetail:
        return await self._detail(await self.shipments.get_row(shipment_id), str(shipment_id))

    async def detail_by_number(self, shipment_number: str) -> ShipmentDetail:
        row = await self.shipments.get_row_by_number(shipment_number)
        return await self._detail(row, shipment_number)

    async def raise_exception(self, shipment_id: uuid.UUID, data: ExceptionCreate) -> ExceptionRead:
        # Same lock as event recording: a manual exception and an automatic one (raised while
        # an event is recorded) for the same shipment must not interleave.
        shipment = await self.lock(shipment_id)
        return await self.exceptions.raise_new(
            shipment.id, data.type, data.severity, data.description
        )

    async def _detail(self, row: ShipmentRow | None, reference: str) -> ShipmentDetail:
        if row is None:
            raise NotFoundError(f"Shipment {reference} not found", details={"shipment": reference})
        shipment = row[0]
        latest = await self.events.latest(shipment.id)
        return ShipmentDetail(
            **to_read(row, datetime.now(UTC)).model_dump(),
            latest_event=TrackingEventRead.model_validate(latest) if latest else None,
            active_exceptions=await self.exceptions.active_for_shipment(shipment.id),
        )


def _not_found(shipment_id: uuid.UUID) -> NotFoundError:
    return NotFoundError(f"Shipment {shipment_id} not found", details={"id": str(shipment_id)})
