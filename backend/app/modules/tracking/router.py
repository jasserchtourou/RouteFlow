"""HTTP layer for tracking events."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.dependencies import DbSession
from app.core.errors import error_responses
from app.core.pagination import Page
from app.modules.tracking.results import EventRecorded
from app.modules.tracking.schemas import (
    EventFeedParams,
    FeedEventRead,
    TrackingEventCreate,
    TrackingEventRead,
)
from app.modules.tracking.service import TrackingService

router = APIRouter(prefix="/shipments/{shipment_id}", tags=["tracking"])


def get_tracking_service(session: DbSession) -> TrackingService:
    return TrackingService(session)


Service = Annotated[TrackingService, Depends(get_tracking_service)]


@router.get(
    "/tracking",
    response_model=list[TrackingEventRead],
    responses=error_responses(404),
    summary="Tracking history of a shipment (oldest first)",
)
async def tracking_history(shipment_id: uuid.UUID, service: Service) -> list[TrackingEventRead]:
    return await service.history(shipment_id)


@router.post(
    "/events",
    response_model=EventRecorded,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(404, 409, 422),
    summary="Record a tracking event (advances the shipment status for lifecycle events)",
)
async def record_event(
    shipment_id: uuid.UUID, payload: TrackingEventCreate, service: Service
) -> EventRecorded:
    return await service.record(shipment_id, payload)


feed_router = APIRouter(prefix="/events", tags=["tracking"])


@feed_router.get(
    "",
    response_model=Page[FeedEventRead],
    summary="Network-wide event feed, newest first",
)
async def event_feed(
    params: Annotated[EventFeedParams, Query()], service: Service
) -> Page[FeedEventRead]:
    return await service.feed(params)
