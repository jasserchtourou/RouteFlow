"""What each tracking event means for the shipment (pure functions)."""

from app.modules.exceptions.models import ExceptionSeverity
from app.modules.shipments.models import ShipmentStatus
from app.modules.tracking.models import TrackingEventType

# Lifecycle events move the shipment to a new status.
STATUS_FOR_EVENT: dict[TrackingEventType, ShipmentStatus] = {
    TrackingEventType.PICKED: ShipmentStatus.PICKED,
    TrackingEventType.PACKED: ShipmentStatus.PACKED,
    TrackingEventType.LOADED: ShipmentStatus.LOADED,
    TrackingEventType.DEPARTED: ShipmentStatus.IN_TRANSIT,
    TrackingEventType.OUT_FOR_DELIVERY: ShipmentStatus.OUT_FOR_DELIVERY,
    TrackingEventType.DELIVERED: ShipmentStatus.DELIVERED,
}
# Informational events are recorded without a status change (some raise an exception).
INFORMATIONAL_EVENTS = frozenset(
    {
        TrackingEventType.CHECKPOINT,
        TrackingEventType.ARRIVED_HUB,
        TrackingEventType.DELAY_REPORTED,
        TrackingEventType.TEMPERATURE_ALERT,
    }
)
# CREATED is written by the system when a shipment is created, never posted by clients.
POSTABLE_EVENTS = frozenset(STATUS_FOR_EVENT) | INFORMATIONAL_EVENTS

# Cold chain: allowed band for temperature-controlled goods (2-8 °C, typical for pharma/dairy).
ALLOWED_TEMPERATURE_C = (2.0, 8.0)
CRITICAL_DEVIATION_C = 3.0  # this far outside the band, goods are likely unusable
LONG_DELAY_MINUTES = 120


def temperature_deviation(temperature_c: float) -> float:
    """Degrees outside the allowed band (0 when inside)."""
    low, high = ALLOWED_TEMPERATURE_C
    return max(low - temperature_c, temperature_c - high, 0.0)


def temperature_severity(temperature_c: float) -> ExceptionSeverity:
    if temperature_deviation(temperature_c) >= CRITICAL_DEVIATION_C:
        return ExceptionSeverity.CRITICAL
    return ExceptionSeverity.HIGH


def delay_severity(delay_minutes: int) -> ExceptionSeverity:
    return (
        ExceptionSeverity.HIGH if delay_minutes >= LONG_DELAY_MINUTES else ExceptionSeverity.MEDIUM
    )
