"""Recording tracking events: the write path that moves shipments through their lifecycle.

One event can touch four tables (event, shipment, exception, order). All of it happens in a
single transaction: either everything is stored, or nothing is.
"""

import logging
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import BusinessRuleError, ConflictError
from app.core.pagination import Page
from app.modules.exceptions.models import ExceptionType, ShipmentException
from app.modules.exceptions.service import ExceptionService
from app.modules.orders.service import OrderService
from app.modules.shipments import rules as shipment_rules
from app.modules.shipments.models import Shipment, ShipmentStatus, TemperatureStatus
from app.modules.shipments.service import ShipmentService
from app.modules.tracking import rules
from app.modules.tracking.models import TrackingEvent, TrackingEventType
from app.modules.tracking.repository import TrackingRepository
from app.modules.tracking.results import EventRecorded
from app.modules.tracking.schemas import (
    EventFeedParams,
    FeedEventRead,
    TrackingEventCreate,
    TrackingEventRead,
)

logger = logging.getLogger(__name__)


class NotTemperatureControlledError(ConflictError):
    code = "not_temperature_controlled"


class EventOutOfOrderError(BusinessRuleError):
    code = "event_out_of_order"


class TrackingService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.events = TrackingRepository(session)
        self.shipments = ShipmentService(session)
        self.exceptions = ExceptionService(session)
        self.orders = OrderService(session)

    async def history(self, shipment_id: uuid.UUID) -> list[TrackingEventRead]:
        shipment = await self.shipments.get(shipment_id)
        return [TrackingEventRead.model_validate(e) for e in await self.events.history(shipment.id)]

    async def feed(self, params: EventFeedParams) -> Page[FeedEventRead]:
        rows, total = await self.events.feed(params)
        items = [
            FeedEventRead(
                **TrackingEventRead.model_validate(event).model_dump(),
                shipment_number=number,
                origin=origin,
                destination=destination,
            )
            for event, number, origin, destination in rows
        ]
        return Page[FeedEventRead](
            items=items, total=total, limit=params.limit, offset=params.offset
        )

    async def record(self, shipment_id: uuid.UUID, data: TrackingEventCreate) -> EventRecorded:
        shipment = await self.shipments.lock(shipment_id)
        occurred_at = data.occurred_at or datetime.now(UTC)
        target = rules.STATUS_FOR_EVENT.get(data.event_type)

        # 1. Validate everything before changing anything.
        shipment_rules.ensure_open(shipment.status)
        await self._ensure_chronological(shipment, occurred_at, is_lifecycle=target is not None)
        if target is not None:
            shipment_rules.ensure_transition_allowed(shipment.status, target)
            await self.orders.ensure_can_follow_shipment(shipment.order_id)
        if (
            data.event_type == TrackingEventType.TEMPERATURE_ALERT
            and shipment.temperature_status == TemperatureStatus.NOT_APPLICABLE
        ):
            raise NotTemperatureControlledError(
                f"{shipment.shipment_number} carries ambient goods; no temperature monitoring"
            )

        # 2. Apply the event and its consequences.
        event = TrackingEvent(
            shipment_id=shipment.id,
            event_type=data.event_type,
            location=data.location,
            occurred_at=occurred_at,
            details=data.details,
        )
        self.events.add(event)
        if target is not None:
            self._advance(shipment, target, occurred_at)
            await self.orders.follow_shipment(shipment.order_id, target)
        raised = await self._detect_exceptions(shipment, data)

        # 3. Commit once: event, shipment, exceptions and order change together or not at all.
        await self.session.commit()
        logger.info(
            "%s recorded for %s (status %s)",
            data.event_type,
            shipment.shipment_number,
            shipment.status,
        )
        return EventRecorded(
            event=TrackingEventRead.model_validate(event),
            shipment=await self.shipments.read(shipment.id),
            exceptions=await self.exceptions.read_many([e.id for e in raised]),
        )

    async def _ensure_chronological(
        self, shipment: Shipment, occurred_at: datetime, *, is_lifecycle: bool
    ) -> None:
        if occurred_at < shipment.created_at:
            raise EventOutOfOrderError("Event cannot precede the creation of the shipment")
        latest = await self.events.latest_occurred_at(shipment.id)
        # Late-synced informational scans are fine, but status changes must move forward in time.
        if is_lifecycle and latest is not None and occurred_at < latest:
            raise EventOutOfOrderError(
                "A status change cannot be dated before the latest tracking event",
                details={"latest_event_at": latest.isoformat()},
            )

    @staticmethod
    def _advance(shipment: Shipment, target: ShipmentStatus, occurred_at: datetime) -> None:
        shipment.status = target
        if target == ShipmentStatus.DELIVERED:
            shipment.actual_delivery = occurred_at

    async def _detect_exceptions(
        self, shipment: Shipment, data: TrackingEventCreate
    ) -> list[ShipmentException]:
        """Informational events that indicate a problem raise (or escalate) an exception."""
        if data.event_type == TrackingEventType.TEMPERATURE_ALERT:
            reading = float(data.details["temperature_c"])  # type: ignore[arg-type]  # validated
            if rules.temperature_deviation(reading) == 0:
                return []  # alert cleared / reading back inside the band
            shipment.temperature_status = TemperatureStatus.DEVIATION
            low, high = rules.ALLOWED_TEMPERATURE_C
            return [
                await self.exceptions.raise_or_escalate(
                    shipment.id,
                    ExceptionType.TEMPERATURE_DEVIATION,
                    rules.temperature_severity(reading),
                    f"Temperature {reading:.1f} °C at {data.location}; allowed {low}-{high} °C.",
                )
            ]
        if data.event_type == TrackingEventType.DELAY_REPORTED:
            minutes = int(data.details["delay_minutes"])  # type: ignore[arg-type]  # validated
            shipment.estimated_delivery += timedelta(minutes=minutes)
            reason = data.details.get("reason") or "no reason given"
            return [
                await self.exceptions.raise_or_escalate(
                    shipment.id,
                    ExceptionType.DELAYED,
                    rules.delay_severity(minutes),
                    f"Delay of {minutes} min reported at {data.location} ({reason}).",
                )
            ]
        return []
