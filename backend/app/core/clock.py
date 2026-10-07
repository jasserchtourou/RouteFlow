"""Injectable clock and business-day helpers.

Code that depends on "now" takes it from here, so tests can freeze time instead of racing the
real clock (e.g. deliveries just before/after midnight).
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Annotated
from zoneinfo import ZoneInfo

from fastapi import Depends


def utcnow() -> datetime:
    return datetime.now(UTC)


def get_clock() -> Callable[[], datetime]:
    """FastAPI dependency; tests override it with a fixed time."""
    return utcnow


Clock = Annotated[Callable[[], datetime], Depends(get_clock)]


@dataclass(frozen=True)
class DayWindow:
    """A calendar day in the business timezone, as a half-open UTC interval [start, end)."""

    start: datetime
    end: datetime


def business_day(now: datetime, timezone: str, days_ago: int = 0) -> DayWindow:
    zone = ZoneInfo(timezone)
    local_midnight = now.astimezone(zone).replace(hour=0, minute=0, second=0, microsecond=0)
    start = local_midnight - timedelta(days=days_ago)
    # Add a calendar day in local time (23 or 25 hours on DST switch days), then go back to UTC.
    end = (start + timedelta(days=1)).replace(tzinfo=zone)
    return DayWindow(start.astimezone(UTC), end.astimezone(UTC))
