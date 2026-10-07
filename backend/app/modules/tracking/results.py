"""Response of POST /shipments/{id}/events: the event plus everything it changed.

Separate from tracking/schemas.py to avoid an import cycle (shipment schemas embed events).
"""

from pydantic import BaseModel, Field

from app.modules.exceptions.schemas import ExceptionRead
from app.modules.shipments.schemas import ShipmentRead
from app.modules.tracking.schemas import TrackingEventRead


class EventRecorded(BaseModel):
    event: TrackingEventRead
    shipment: ShipmentRead = Field(description="Shipment state after the event")
    exceptions: list[ExceptionRead] = Field(
        description="Exceptions raised or escalated by this event"
    )
