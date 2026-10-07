"""Data access for tracking events (append-only)."""

import uuid
from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import Row, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.querying import contains_any, paginate_rows
from app.modules.shipments.models import Shipment
from app.modules.tracking.models import TrackingEvent
from app.modules.tracking.schemas import EventFeedParams


class TrackingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def history(self, shipment_id: uuid.UUID) -> Sequence[TrackingEvent]:
        result = await self.session.scalars(
            select(TrackingEvent)
            .where(TrackingEvent.shipment_id == shipment_id)
            .order_by(TrackingEvent.occurred_at, TrackingEvent.created_at)
        )
        return result.all()

    async def feed(
        self, params: EventFeedParams
    ) -> tuple[Sequence[Row[TrackingEvent, str, str, str]], int]:
        """Newest events first, across all shipments."""
        query = select(
            TrackingEvent, Shipment.shipment_number, Shipment.origin, Shipment.destination
        ).join(Shipment, Shipment.id == TrackingEvent.shipment_id)
        if params.event_type:
            query = query.where(TrackingEvent.event_type.in_(params.event_type))
        if params.since:
            query = query.where(TrackingEvent.occurred_at >= params.since)
        if params.search:
            query = query.where(
                contains_any(
                    params.search,
                    Shipment.shipment_number,
                    Shipment.origin,
                    Shipment.destination,
                    TrackingEvent.location,
                )
            )
        # created_at and id make the order total, so rows cannot swap between pages.
        query = query.order_by(
            TrackingEvent.occurred_at.desc(), TrackingEvent.created_at.desc(), TrackingEvent.id
        )
        return await paginate_rows(self.session, query, params)

    async def latest(self, shipment_id: uuid.UUID) -> TrackingEvent | None:
        return await self.session.scalar(
            select(TrackingEvent)
            .where(TrackingEvent.shipment_id == shipment_id)
            .order_by(TrackingEvent.occurred_at.desc(), TrackingEvent.created_at.desc())
            .limit(1)
        )

    async def latest_occurred_at(self, shipment_id: uuid.UUID) -> datetime | None:
        return await self.session.scalar(
            select(func.max(TrackingEvent.occurred_at)).where(
                TrackingEvent.shipment_id == shipment_id
            )
        )

    def add(self, event: TrackingEvent) -> None:
        self.session.add(event)
