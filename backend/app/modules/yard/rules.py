"""Yard business definitions: the life of a truck visit, derived from its timeline and the clock.

Nothing here is stored. A dock appointment holds three timestamps (arrives_at, docked_at,
departs_at); where the truck is *now* follows from comparing them with the current time. That
keeps the data free of stale state and makes every rule testable with a plain `datetime`.

    arrives_at   truck enters the yard (before: EN_ROUTE on the road, WAITING after)
    docked_at    truck starts reversing into the dock door (DOCKED for DOCKING_TIME)
    departs_at   work is finished and the truck pulls away (DEPARTED for LEAVING_TIME)
"""

import math
from collections.abc import Iterable, Sequence
from datetime import datetime, timedelta
from enum import StrEnum

from app.modules.warehouses.models import DockDirection, DockStatus, EquipmentStatus

APPROACH_TIME = timedelta(minutes=6)  # how long before arrival a truck is visible on the road
DOCKING_TIME = timedelta(minutes=1)  # reversing into the door before pallets move
LEAVING_TIME = timedelta(minutes=2)  # how long a departed truck stays visible


class VisitState(StrEnum):
    SCHEDULED = "SCHEDULED"  # too far in the future to be on screen
    EN_ROUTE = "EN_ROUTE"  # driving towards the site
    WAITING = "WAITING"  # in the yard, dock not free yet
    DOCKED = "DOCKED"  # reversing into the dock door
    LOADING = "LOADING"  # outbound: pallets going onto the truck
    UNLOADING = "UNLOADING"  # inbound: pallets coming off the truck
    DEPARTED = "DEPARTED"  # pulling away from the site
    COMPLETED = "COMPLETED"  # gone


class DockState(StrEnum):
    AVAILABLE = "AVAILABLE"
    BOOKED = "BOOKED"  # a truck is on its way or waiting for this door
    OCCUPIED = "OCCUPIED"  # a truck is at the door
    OUT_OF_SERVICE = "OUT_OF_SERVICE"


WORKING_STATES = frozenset({VisitState.LOADING, VisitState.UNLOADING})
AT_DOOR_STATES = frozenset({VisitState.DOCKED, *WORKING_STATES})
ON_SITE_STATES = frozenset({VisitState.WAITING, *AT_DOOR_STATES})
VISIBLE_STATES = frozenset({VisitState.EN_ROUTE, *ON_SITE_STATES, VisitState.DEPARTED})


def visit_state(
    arrives_at: datetime,
    docked_at: datetime,
    departs_at: datetime,
    direction: DockDirection,
    now: datetime,
) -> VisitState:
    if now < arrives_at - APPROACH_TIME:
        return VisitState.SCHEDULED
    if now < arrives_at:
        return VisitState.EN_ROUTE
    if now < docked_at:
        return VisitState.WAITING
    if now < docked_at + DOCKING_TIME:
        return VisitState.DOCKED
    if now < departs_at:
        return VisitState.LOADING if direction == DockDirection.OUTBOUND else VisitState.UNLOADING
    if now < departs_at + LEAVING_TIME:
        return VisitState.DEPARTED
    return VisitState.COMPLETED


def pallets_done(docked_at: datetime, departs_at: datetime, total: int, now: datetime) -> int:
    """Pallets moved so far: none until the truck is docked, then a steady rate until it leaves."""
    work_start = docked_at + DOCKING_TIME
    if now <= work_start:
        return 0
    duration = (departs_at - work_start).total_seconds()
    if duration <= 0 or now >= departs_at:
        return total
    return min(total, math.floor(total * (now - work_start).total_seconds() / duration))


def minutes_remaining(
    state: VisitState, docked_at: datetime, departs_at: datetime, now: datetime
) -> int | None:
    """Minutes until the next milestone that matters to the operator, rounded up.

    EN_ROUTE / WAITING: until the truck reaches the dock ("due in 3 min").
    DOCKED / LOADING / UNLOADING: until it leaves ("13 min left").
    """
    if state in {VisitState.EN_ROUTE, VisitState.WAITING}:
        target = docked_at
    elif state in AT_DOOR_STATES:
        target = departs_at
    else:
        return None
    return max(0, math.ceil((target - now).total_seconds() / 60))


def dock_state(status: DockStatus, visits: Iterable[VisitState]) -> DockState:
    """Occupancy of one dock door, from its physical status and its visits' states."""
    if status == DockStatus.OUT_OF_SERVICE:
        return DockState.OUT_OF_SERVICE
    states = set(visits)
    if states & AT_DOOR_STATES:
        return DockState.OCCUPIED
    if states & {VisitState.EN_ROUTE, VisitState.WAITING}:
        return DockState.BOOKED
    return DockState.AVAILABLE


MAX_FORKLIFTS_PER_DOCK = 2  # one on each side of the truck; more would have no room to work


def assign_equipment(
    equipment: Sequence[tuple[str, EquipmentStatus]], working_docks: Sequence[str]
) -> dict[str, str]:
    """Which dock each busy forklift is serving: active units (by code) are spread round-robin
    over the docks that currently have pallets moving, at most MAX_FORKLIFTS_PER_DOCK each.
    Idle, charging and maintenance units, and active units beyond that capacity, get none."""
    if not working_docks:
        return {}
    active = sorted(code for code, status in equipment if status == EquipmentStatus.ACTIVE)
    load = dict.fromkeys(working_docks, 0)
    assigned: dict[str, str] = {}
    for index, code in enumerate(active):
        for step in range(len(working_docks)):
            dock = working_docks[(index + step) % len(working_docks)]
            if load[dock] < MAX_FORKLIFTS_PER_DOCK:
                load[dock] += 1
                assigned[code] = dock
                break
    return assigned
