from datetime import UTC, datetime

import pytest

from app.core.clock import business_day
from app.modules.dashboard.rules import change_in_points, on_time_rate
from app.modules.routes.models import RiskLevel, RouteStatus
from app.modules.routes.rules import RouteSignals, assess_route_risk
from app.modules.vehicles.rules import fleet_utilization_pct, is_low_fuel


def _signals(**overrides: object) -> RouteSignals:
    values: dict[str, object] = {
        "planned_risk": RiskLevel.LOW,
        "status": RouteStatus.ACTIVE,
        "active_shipments": 0,
        "delayed_shipments": 0,
        "max_delay_minutes": 0,
        "serious_exceptions": 0,
    }
    return RouteSignals(**{**values, **overrides})  # type: ignore[arg-type]


def test_quiet_route_keeps_its_planned_risk() -> None:
    assessment = assess_route_risk(_signals(active_shipments=4))

    assert assessment.score == 10
    assert assessment.level == RiskLevel.LOW
    assert assessment.factors == ["Planned risk LOW (+10)"]


def test_live_signals_raise_the_risk_and_explain_why() -> None:
    assessment = assess_route_risk(
        _signals(
            planned_risk=RiskLevel.MEDIUM,
            status=RouteStatus.DELAYED,
            active_shipments=6,
            delayed_shipments=3,
            max_delay_minutes=130,
            serious_exceptions=1,
        )
    )

    # 25 planned + 15 delayed + 6 lateness + 10 exceptions + 10 flagged = 66
    assert assessment.score == 66
    assert assessment.level == RiskLevel.HIGH
    assert assessment.factors == [
        "Planned risk MEDIUM (+25)",
        "3 of 6 active shipments delayed (+15)",
        "Worst delay 130 min (+6)",
        "1 high/critical exception(s) open (+10)",
        "Route flagged DELAYED (+10)",
    ]


def test_contributions_are_capped_and_score_stays_within_100() -> None:
    assessment = assess_route_risk(
        _signals(
            planned_risk=RiskLevel.CRITICAL,
            status=RouteStatus.DELAYED,
            active_shipments=50,
            delayed_shipments=50,
            max_delay_minutes=10_000,
            serious_exceptions=50,
        )
    )

    assert assessment.score == 100
    assert assessment.level == RiskLevel.CRITICAL


@pytest.mark.parametrize(
    ("score_inputs", "level"),
    [
        ({"planned_risk": RiskLevel.MEDIUM}, RiskLevel.LOW),  # 25
        ({"planned_risk": RiskLevel.MEDIUM, "delayed_shipments": 1}, RiskLevel.MEDIUM),  # 30
        ({"planned_risk": RiskLevel.HIGH, "delayed_shipments": 2}, RiskLevel.HIGH),  # 55
        ({"planned_risk": RiskLevel.CRITICAL, "delayed_shipments": 2}, RiskLevel.CRITICAL),  # 75
    ],
)
def test_level_thresholds(score_inputs: dict[str, object], level: RiskLevel) -> None:
    assert assess_route_risk(_signals(**score_inputs)).level == level


def test_fleet_rules() -> None:
    assert is_low_fuel(19.9)
    assert not is_low_fuel(20.0)
    assert fleet_utilization_pct(18, 21) == 85.7
    assert fleet_utilization_pct(0, 0) is None


def test_delivery_performance_rules() -> None:
    assert on_time_rate(9, 10) == 90.0
    assert on_time_rate(0, 0) is None
    assert change_in_points(92.0, 95.5) == -3.5
    assert change_in_points(None, 90.0) is None


def test_business_day_uses_local_midnight() -> None:
    # 00:30 in Berlin on 7 October is still 6 October in UTC.
    window = business_day(datetime(2026, 10, 6, 22, 30, tzinfo=UTC), "Europe/Berlin")

    assert window.start == datetime(2026, 10, 6, 22, 0, tzinfo=UTC)
    assert window.end == datetime(2026, 10, 7, 22, 0, tzinfo=UTC)


def test_business_day_handles_daylight_saving_change() -> None:
    # Clocks go back on 25 October 2026: that business day has 25 hours.
    window = business_day(datetime(2026, 10, 25, 12, 0, tzinfo=UTC), "Europe/Berlin")

    assert (window.end - window.start).total_seconds() == 25 * 3600
    yesterday = business_day(datetime(2026, 10, 25, 12, 0, tzinfo=UTC), "Europe/Berlin", 1)
    assert yesterday.end == window.start  # consecutive days never overlap or leave gaps
