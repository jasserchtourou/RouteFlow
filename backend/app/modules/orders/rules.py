"""Order business rules, as pure functions: no database, no HTTP, trivially unit-testable."""

from app.core.errors import ConflictError
from app.modules.orders.models import OrderStatus

ALLOWED_TRANSITIONS: dict[OrderStatus, frozenset[OrderStatus]] = {
    OrderStatus.PENDING: frozenset({OrderStatus.CONFIRMED, OrderStatus.CANCELLED}),
    OrderStatus.CONFIRMED: frozenset({OrderStatus.PROCESSING, OrderStatus.CANCELLED}),
    OrderStatus.PROCESSING: frozenset({OrderStatus.SHIPPED, OrderStatus.CANCELLED}),
    OrderStatus.SHIPPED: frozenset({OrderStatus.DELIVERED}),
    OrderStatus.DELIVERED: frozenset(),
    OrderStatus.CANCELLED: frozenset(),
}

# Closed orders are historical records and must not change.
CLOSED_STATUSES = frozenset({OrderStatus.DELIVERED, OrderStatus.CANCELLED})
# Where the goods go can only change before warehouse work has started.
ROUTING_EDITABLE_STATUSES = frozenset({OrderStatus.PENDING, OrderStatus.CONFIRMED})
ROUTING_FIELDS = frozenset({"origin", "destination"})


class InvalidStatusTransitionError(ConflictError):
    code = "invalid_status_transition"


class OrderNotEditableError(ConflictError):
    code = "order_not_editable"


def ensure_transition_allowed(current: OrderStatus, target: OrderStatus) -> None:
    if target == current:
        return  # idempotent: setting the same status again is a no-op
    if target not in ALLOWED_TRANSITIONS[current]:
        raise InvalidStatusTransitionError(
            f"Order status cannot change from {current} to {target}",
            details={
                "current": current,
                "requested": target,
                "allowed": sorted(ALLOWED_TRANSITIONS[current]),
            },
        )


def ensure_editable(status: OrderStatus, changed_fields: set[str]) -> None:
    if status in CLOSED_STATUSES:
        raise OrderNotEditableError(f"A {status} order can no longer be changed")
    routing_changes = changed_fields & ROUTING_FIELDS
    if routing_changes and status not in ROUTING_EDITABLE_STATUSES:
        raise OrderNotEditableError(
            f"{', '.join(sorted(routing_changes))} cannot change once an order is {status}",
            details={"fields": sorted(routing_changes), "status": status},
        )


# The forward path an order takes as its shipments progress (CANCELLED is not on it).
FORWARD_PATH: tuple[OrderStatus, ...] = (
    OrderStatus.PENDING,
    OrderStatus.CONFIRMED,
    OrderStatus.PROCESSING,
    OrderStatus.SHIPPED,
    OrderStatus.DELIVERED,
)


class OrderCancelledError(ConflictError):
    code = "order_cancelled"


def advance_to(current: OrderStatus, target: OrderStatus) -> OrderStatus:
    """Status after shipment progress implies `target`: forward only, never backwards.

    Shipment events are facts from the floor ("goods were picked"), so the order follows them
    even if intermediate order steps (e.g. CONFIRMED) were never set explicitly.
    """
    if current == OrderStatus.CANCELLED:
        raise OrderCancelledError("The order was cancelled; its shipment cannot progress")
    if FORWARD_PATH.index(target) <= FORWARD_PATH.index(current):
        return current
    return target
