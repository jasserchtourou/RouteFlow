"""Yard simulator: keeps a rolling schedule of truck visits so a demo site is always alive.

It is deliberately small and deterministic. For each dock it plans visits one after another
(`plan_visit`), seeded by (warehouse, dock, sequence), until the schedule reaches `HORIZON`
into the future. Calling it again is a no-op until time has moved on, so it is safe to call from
every scene request. With real appointment data (a TMS integration) it would simply be switched
off via `YARD_SIMULATION_ENABLED=false`.
"""

import random
from dataclasses import dataclass
from datetime import datetime, timedelta

from app.modules.yard.rules import LEAVING_TIME

HORIZON = timedelta(hours=3)  # schedule is kept this far ahead of "now"
RETENTION = timedelta(hours=36)  # finished visits are kept this long (for "trucks today")
FIRST_VISIT_OFFSET = timedelta(minutes=25)  # a new dock starts mid-shift, not empty

CARRIERS = (
    "Nordlicht Spedition",
    "Harzer Logistik",
    "Elbe Cargo",
    "Weserfracht",
    "Leine Express",
    "Heide Transporte",
)


@dataclass(frozen=True)
class PlannedVisit:
    sequence: int
    truck_code: str
    carrier: str
    pallets_total: int
    arrives_at: datetime
    docked_at: datetime
    departs_at: datetime


def plan_visit(
    warehouse_code: str, dock_code: str, sequence: int, dock_free_from: datetime
) -> PlannedVisit:
    """Plan the next truck for a dock that is free from `dock_free_from`.

    Seeded by (warehouse, dock, sequence): the same inputs always give the same visit, so two
    app instances (or a test) agree on what the schedule looks like.
    """
    rng = random.Random(f"{warehouse_code}/{dock_code}/{sequence}")  # noqa: S311 (reproducible demo data)
    gap = timedelta(minutes=rng.randint(2, 12))  # dock stands empty between two trucks
    wait = timedelta(minutes=rng.randint(1, 6))  # truck waits in the yard before reversing in
    work = timedelta(minutes=rng.randint(9, 22))  # pallets moving
    docked_at = dock_free_from + gap
    return PlannedVisit(
        sequence=sequence,
        truck_code=f"TRK-{rng.randint(2000, 2999)}",
        carrier=rng.choice(CARRIERS),
        pallets_total=rng.randint(4, 24),
        arrives_at=docked_at - wait,
        docked_at=docked_at,
        departs_at=docked_at + work,
    )


def plan_until(
    warehouse_code: str,
    dock_code: str,
    next_sequence: int,
    dock_free_from: datetime,
    until: datetime,
) -> list[PlannedVisit]:
    """Plan visits back to back until the last one departs at or after `until`."""
    visits: list[PlannedVisit] = []
    sequence = next_sequence
    free_from = dock_free_from
    while free_from < until:
        visit = plan_visit(warehouse_code, dock_code, sequence, free_from)
        visits.append(visit)
        # The next truck may only back in once this one has pulled away.
        free_from = visit.departs_at + LEAVING_TIME
        sequence += 1
    return visits
