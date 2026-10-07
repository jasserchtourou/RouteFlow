"""Business rules and schema validation, without database or HTTP."""

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from pydantic import ValidationError

from app.modules.orders.models import OrderStatus
from app.modules.orders.rules import (
    InvalidStatusTransitionError,
    OrderNotEditableError,
    ensure_editable,
    ensure_transition_allowed,
)
from app.modules.orders.schemas import OrderCreate, OrderListParams, OrderUpdate

S = OrderStatus
FUTURE = datetime.now(UTC) + timedelta(days=2)


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (S.PENDING, S.CONFIRMED),
        (S.PENDING, S.CANCELLED),
        (S.CONFIRMED, S.PROCESSING),
        (S.PROCESSING, S.SHIPPED),
        (S.PROCESSING, S.CANCELLED),
        (S.SHIPPED, S.DELIVERED),
        (S.CONFIRMED, S.CONFIRMED),  # same status: idempotent no-op
    ],
)
def test_allowed_transitions(current: OrderStatus, target: OrderStatus) -> None:
    ensure_transition_allowed(current, target)


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (S.PENDING, S.SHIPPED),  # skipping steps
        (S.PENDING, S.DELIVERED),
        (S.SHIPPED, S.CANCELLED),  # goods already left: cancel is no longer possible
        (S.DELIVERED, S.PENDING),  # terminal states
        (S.CANCELLED, S.CONFIRMED),
        (S.PROCESSING, S.CONFIRMED),  # no going backwards
    ],
)
def test_forbidden_transitions(current: OrderStatus, target: OrderStatus) -> None:
    with pytest.raises(InvalidStatusTransitionError) as error:
        ensure_transition_allowed(current, target)

    assert error.value.details["current"] == current


@pytest.mark.parametrize("status", [S.DELIVERED, S.CANCELLED])
def test_closed_orders_cannot_be_edited(status: OrderStatus) -> None:
    with pytest.raises(OrderNotEditableError):
        ensure_editable(status, {"priority"})


def test_routing_is_frozen_once_processing_started() -> None:
    ensure_editable(S.CONFIRMED, {"destination"})
    ensure_editable(S.PROCESSING, {"priority", "promised_delivery_at"})

    with pytest.raises(OrderNotEditableError, match="destination"):
        ensure_editable(S.PROCESSING, {"destination"})


def _create(**overrides: Any) -> OrderCreate:
    values: dict[str, Any] = {
        "customer_name": "Leinetal Pharma GmbH",
        "origin": "Garbsen",
        "destination": "Hannover",
        "promised_delivery_at": FUTURE,
    }
    return OrderCreate(**{**values, **overrides})


def test_create_strips_whitespace() -> None:
    assert _create(customer_name="  Acme  ").customer_name == "Acme"


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"customer_name": "   "}, "at least 1 character"),
        ({"destination": "garbsen"}, "origin and destination must differ"),
        ({"promised_delivery_at": datetime.now(UTC) - timedelta(hours=1)}, "in the future"),
        ({"promised_delivery_at": datetime(2030, 1, 1)}, "timezone"),  # naive datetime
        ({"status": "DELIVERED"}, "Extra inputs are not permitted"),
        ({"order_number": "ORD-1"}, "Extra inputs are not permitted"),
        ({"priority": "SUPER_URGENT"}, "Input should be"),
    ],
)
def test_create_rejects_invalid_input(overrides: dict[str, Any], message: str) -> None:
    with pytest.raises(ValidationError, match=message):
        _create(**overrides)


def test_update_distinguishes_absent_from_null() -> None:
    assert OrderUpdate(priority="HIGH").changes() == {"priority": "HIGH"}

    with pytest.raises(ValidationError, match="cannot be null: customer_name"):
        OrderUpdate(customer_name=None)


def test_update_requires_at_least_one_field() -> None:
    with pytest.raises(ValidationError, match="at least one field"):
        OrderUpdate()


def test_list_params_reject_inverted_date_range() -> None:
    with pytest.raises(ValidationError, match="created_after"):
        OrderListParams(created_after=FUTURE, created_before=FUTURE - timedelta(days=1))
