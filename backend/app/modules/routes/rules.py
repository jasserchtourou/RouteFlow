"""Route risk assessment: an explainable score built from current operational facts.

The planned `risk_level` stored on a route is the starting point; live signals (delayed
shipments, how late they are, serious incidents, the route being flagged DELAYED) add to it.
Every contribution is returned as a human-readable factor, so dispatchers (and later the AI
agent) can see *why* a route ranks high instead of trusting an opaque number.
"""

from dataclasses import dataclass

from app.modules.routes.models import RiskLevel, RouteStatus

BASE_SCORE = {RiskLevel.LOW: 10, RiskLevel.MEDIUM: 25, RiskLevel.HIGH: 45, RiskLevel.CRITICAL: 65}
POINTS_PER_DELAYED_SHIPMENT, MAX_DELAYED_POINTS = 5, 20
MINUTES_PER_DELAY_POINT, MAX_LATENESS_POINTS = 20, 15
POINTS_PER_SERIOUS_EXCEPTION, MAX_EXCEPTION_POINTS = 10, 20
DELAYED_STATUS_POINTS = 10
# Score thresholds for the assessed level (score < threshold -> level).
LEVEL_THRESHOLDS = ((30, RiskLevel.LOW), (55, RiskLevel.MEDIUM), (75, RiskLevel.HIGH))


@dataclass(frozen=True)
class RouteSignals:
    planned_risk: RiskLevel
    status: RouteStatus
    active_shipments: int
    delayed_shipments: int
    max_delay_minutes: int
    serious_exceptions: int  # active HIGH / CRITICAL incidents on the route's shipments


@dataclass(frozen=True)
class RiskAssessment:
    score: int  # 0-100
    level: RiskLevel
    factors: list[str]


def assess_route_risk(signals: RouteSignals) -> RiskAssessment:
    score = BASE_SCORE[signals.planned_risk]
    factors = [f"Planned risk {signals.planned_risk} (+{score})"]

    def add(points: int, reason: str) -> None:
        nonlocal score
        if points > 0:
            score += points
            factors.append(f"{reason} (+{points})")

    add(
        min(MAX_DELAYED_POINTS, POINTS_PER_DELAYED_SHIPMENT * signals.delayed_shipments),
        f"{signals.delayed_shipments} of {signals.active_shipments} active shipments delayed",
    )
    add(
        min(MAX_LATENESS_POINTS, signals.max_delay_minutes // MINUTES_PER_DELAY_POINT),
        f"Worst delay {signals.max_delay_minutes} min",
    )
    add(
        min(MAX_EXCEPTION_POINTS, POINTS_PER_SERIOUS_EXCEPTION * signals.serious_exceptions),
        f"{signals.serious_exceptions} high/critical exception(s) open",
    )
    if signals.status == RouteStatus.DELAYED:
        add(DELAYED_STATUS_POINTS, "Route flagged DELAYED")

    score = min(score, 100)
    return RiskAssessment(score=score, level=_level_for(score), factors=factors)


def _level_for(score: int) -> RiskLevel:
    for threshold, level in LEVEL_THRESHOLDS:
        if score < threshold:
            return level
    return RiskLevel.CRITICAL
