"""Warehouse business definitions. The models' SQL expressions mirror these functions; a test
checks that Python and SQL always agree."""

from enum import StrEnum

HIGH_UTILIZATION_PCT = 85.0
CRITICAL_UTILIZATION_PCT = 95.0


class UtilizationLevel(StrEnum):
    NORMAL = "NORMAL"
    HIGH = "HIGH"  # little buffer left for inbound peaks
    CRITICAL = "CRITICAL"  # receiving will stall soon


def utilization_pct(used: int, capacity: int) -> float:
    return used * 100.0 / capacity


def utilization_level(pct: float) -> UtilizationLevel:
    if pct >= CRITICAL_UTILIZATION_PCT:
        return UtilizationLevel.CRITICAL
    if pct >= HIGH_UTILIZATION_PCT:
        return UtilizationLevel.HIGH
    return UtilizationLevel.NORMAL
