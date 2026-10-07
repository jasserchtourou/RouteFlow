"""Shipment lifecycle and delay rules (pure functions)."""

from datetime import datetime

from app.core.errors import ConflictError
from app.modules.shipments.models import ShipmentStatus

# The lifecycle is strictly sequential: a shipment cannot skip a step.
LIFECYCLE: tuple[ShipmentStatus, ...] = (
    ShipmentStatus.CREATED,
    ShipmentStatus.PICKED,
    ShipmentStatus.PACKED,
    ShipmentStatus.LOADED,
    ShipmentStatus.IN_TRANSIT,
    ShipmentStatus.OUT_FOR_DELIVERY,
    ShipmentStatus.DELIVERED,
)


class InvalidShipmentTransitionError(ConflictError):
    code = "invalid_status_transition"


class ShipmentClosedError(ConflictError):
    code = "shipment_closed"


def next_status(current: ShipmentStatus) -> ShipmentStatus | None:
    index = LIFECYCLE.index(current)
    return LIFECYCLE[index + 1] if index + 1 < len(LIFECYCLE) else None


def ensure_transition_allowed(current: ShipmentStatus, target: ShipmentStatus) -> None:
    expected = next_status(current)
    if target != expected:
        raise InvalidShipmentTransitionError(
            f"Shipment cannot move from {current} to {target}",
            details={"current": current, "requested": target, "allowed": expected},
        )


def ensure_open(status: ShipmentStatus) -> None:
    if status == ShipmentStatus.DELIVERED:
        raise ShipmentClosedError("Shipment is already delivered; no further events accepted")


def is_delayed(status: ShipmentStatus, estimated_delivery: datetime, now: datetime) -> bool:
    """Still on its way although the estimated delivery time has passed."""
    return status != ShipmentStatus.DELIVERED and estimated_delivery < now


def delay_minutes(
    status: ShipmentStatus,
    estimated_delivery: datetime,
    actual_delivery: datetime | None,
    now: datetime,
) -> int:
    """Minutes past the ETA: so far for open shipments, final for delivered ones."""
    reference = actual_delivery if status == ShipmentStatus.DELIVERED else now
    if reference is None:
        return 0
    return max(0, int((reference - estimated_delivery).total_seconds() // 60))
