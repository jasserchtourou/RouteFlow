from datetime import UTC, datetime, timedelta
from itertools import pairwise

import pytest

from app.modules.exceptions.models import ExceptionSeverity as Sev
from app.modules.exceptions.models import ExceptionStatus as ES
from app.modules.exceptions.rules import (
    InvalidExceptionTransitionError,
    higher_severity,
)
from app.modules.exceptions.rules import ensure_transition_allowed as ensure_exception_transition
from app.modules.orders.models import OrderStatus as OS
from app.modules.orders.rules import OrderCancelledError, advance_to
from app.modules.shipments.models import ShipmentStatus as S
from app.modules.shipments.rules import (
    LIFECYCLE,
    InvalidShipmentTransitionError,
    ShipmentClosedError,
    delay_minutes,
    ensure_open,
    ensure_transition_allowed,
    is_delayed,
)
from app.modules.tracking.models import TrackingEventType
from app.modules.tracking.rules import (
    POSTABLE_EVENTS,
    delay_severity,
    temperature_deviation,
    temperature_severity,
)

NOW = datetime(2026, 10, 7, 12, 0, tzinfo=UTC)


@pytest.mark.parametrize(("current", "target"), list(pairwise(LIFECYCLE)))
def test_each_next_step_is_allowed(current: S, target: S) -> None:
    ensure_transition_allowed(current, target)


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (S.CREATED, S.PACKED),  # skip
        (S.PACKED, S.IN_TRANSIT),  # skip LOADED
        (S.IN_TRANSIT, S.LOADED),  # backwards
        (S.PICKED, S.PICKED),  # same status is not an event
        (S.CREATED, S.DELIVERED),
    ],
)
def test_skipping_or_going_back_is_rejected(current: S, target: S) -> None:
    with pytest.raises(InvalidShipmentTransitionError) as error:
        ensure_transition_allowed(current, target)

    assert error.value.details["allowed"] is not None or current == S.DELIVERED


def test_delivered_shipment_is_closed() -> None:
    ensure_open(S.OUT_FOR_DELIVERY)
    with pytest.raises(ShipmentClosedError):
        ensure_open(S.DELIVERED)


def test_delay_definitions() -> None:
    eta = NOW - timedelta(minutes=90)

    assert is_delayed(S.IN_TRANSIT, eta, NOW)
    assert not is_delayed(S.DELIVERED, eta, NOW)
    assert not is_delayed(S.IN_TRANSIT, NOW + timedelta(minutes=1), NOW)
    assert delay_minutes(S.IN_TRANSIT, eta, None, NOW) == 90
    assert delay_minutes(S.DELIVERED, eta, eta + timedelta(minutes=30), NOW) == 30  # final
    assert delay_minutes(S.DELIVERED, eta, eta - timedelta(minutes=30), NOW) == 0  # early


@pytest.mark.parametrize(
    ("reading", "deviation", "severity"),
    [(5.0, 0.0, None), (2.0, 0.0, None), (9.4, 1.4, Sev.HIGH), (11.0, 3.0, Sev.CRITICAL),
     (-2.0, 4.0, Sev.CRITICAL)],
)  # fmt: skip
def test_temperature_rules(reading: float, deviation: float, severity: Sev | None) -> None:
    assert temperature_deviation(reading) == pytest.approx(deviation)
    if severity:
        assert temperature_severity(reading) == severity


def test_delay_severity() -> None:
    assert delay_severity(45) == Sev.MEDIUM
    assert delay_severity(120) == Sev.HIGH


def test_created_events_are_system_only() -> None:
    assert TrackingEventType.CREATED not in POSTABLE_EVENTS
    assert TrackingEventType.DELIVERED in POSTABLE_EVENTS


@pytest.mark.parametrize(
    ("current", "target", "allowed"),
    [
        (ES.OPEN, ES.INVESTIGATING, True),
        (ES.OPEN, ES.RESOLVED, True),
        (ES.INVESTIGATING, ES.RESOLVED, True),
        (ES.INVESTIGATING, ES.OPEN, False),
        (ES.RESOLVED, ES.OPEN, False),
    ],
)
def test_exception_transitions(current: ES, target: ES, allowed: bool) -> None:
    if allowed:
        ensure_exception_transition(current, target)
    else:
        with pytest.raises(InvalidExceptionTransitionError):
            ensure_exception_transition(current, target)


def test_escalation_keeps_the_higher_severity() -> None:
    assert higher_severity(Sev.MEDIUM, Sev.HIGH) == Sev.HIGH
    assert higher_severity(Sev.CRITICAL, Sev.LOW) == Sev.CRITICAL


@pytest.mark.parametrize(
    ("current", "target", "expected"),
    [
        (OS.PENDING, OS.PROCESSING, OS.PROCESSING),  # jumps over CONFIRMED: floor facts win
        (OS.SHIPPED, OS.PROCESSING, OS.SHIPPED),  # never backwards
        (OS.SHIPPED, OS.DELIVERED, OS.DELIVERED),
        (OS.DELIVERED, OS.DELIVERED, OS.DELIVERED),
    ],
)
def test_order_follows_shipment_forward_only(current: OS, target: OS, expected: OS) -> None:
    assert advance_to(current, target) == expected


def test_cancelled_order_blocks_shipment_progress() -> None:
    with pytest.raises(OrderCancelledError):
        advance_to(OS.CANCELLED, OS.PROCESSING)


def test_delay_minutes_is_zero_for_a_delivered_shipment_without_delivery_time() -> None:
    """The database allows DELIVERED with no actual_delivery; the rule must not crash on it."""
    assert delay_minutes(S.DELIVERED, NOW - timedelta(hours=1), None, NOW) == 0
