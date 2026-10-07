"""Fleet rules (pure functions)."""

from app.modules.vehicles.models import VehicleStatus

LOW_FUEL_PCT = 20.0  # below this a vehicle should refuel before taking a new tour
# Vehicles that could be dispatched (maintenance/offline ones cannot).
OPERATIONAL_STATUSES = frozenset({VehicleStatus.AVAILABLE, VehicleStatus.IN_TRANSIT})


def is_low_fuel(fuel_level: float) -> bool:
    return fuel_level < LOW_FUEL_PCT


def fleet_utilization_pct(in_transit: int, operational: int) -> float | None:
    """Share of dispatchable vehicles currently on the road."""
    if operational == 0:
        return None
    return round(in_transit * 100.0 / operational, 1)
