import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated, Self

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from app.core.pagination import PageParams
from app.core.types import SearchTerm, text
from app.modules.tracking.models import TrackingEventType
from app.modules.tracking.rules import POSTABLE_EVENTS

# Scanners and telematics clocks drift a little; anything further ahead is a client error.
MAX_CLOCK_SKEW = timedelta(minutes=5)
DetailValue = str | int | float | bool | None


class TrackingEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    shipment_id: uuid.UUID
    event_type: TrackingEventType
    location: str
    occurred_at: datetime
    details: dict[str, object]
    created_at: datetime


class FeedEventRead(TrackingEventRead):
    """A tracking event in the network-wide feed: it also says which shipment it belongs to."""

    shipment_number: str
    origin: str
    destination: str


class EventFeedParams(PageParams):
    model_config = ConfigDict(extra="forbid")

    event_type: list[TrackingEventType] | None = Field(default=None, description="Repeatable")
    search: SearchTerm | None = Field(
        default=None, description="Substring of shipment number, location, origin or destination"
    )
    since: AwareDatetime | None = Field(default=None, description="Only events at or after this")


class TrackingEventCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_type: TrackingEventType
    location: Annotated[str, text(120)]
    occurred_at: AwareDatetime | None = Field(default=None, description="Defaults to now")
    details: dict[Annotated[str, text(40)], DetailValue] = Field(
        default_factory=dict, max_length=20
    )

    @model_validator(mode="after")
    def _validate(self) -> Self:
        if self.event_type not in POSTABLE_EVENTS:
            raise ValueError(f"{self.event_type} events are created by the system")
        if self.occurred_at and self.occurred_at > datetime.now(UTC) + MAX_CLOCK_SKEW:
            raise ValueError("occurred_at cannot be in the future")
        if self.event_type == TrackingEventType.TEMPERATURE_ALERT:
            reading = self.details.get("temperature_c")
            if isinstance(reading, bool) or not isinstance(reading, int | float):
                raise ValueError("TEMPERATURE_ALERT requires a numeric details.temperature_c")
            if not -40 <= reading <= 60:
                raise ValueError("details.temperature_c must be between -40 and 60")
        if self.event_type == TrackingEventType.DELAY_REPORTED:
            minutes = self.details.get("delay_minutes")
            if (
                isinstance(minutes, bool)
                or not isinstance(minutes, int)
                or not 1 <= minutes <= 2880
            ):
                raise ValueError("DELAY_REPORTED requires details.delay_minutes (1-2880)")
        return self
