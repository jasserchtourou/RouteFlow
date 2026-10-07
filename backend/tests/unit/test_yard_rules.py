"""Pure yard rules and the deterministic simulator (no database)."""

from datetime import UTC, datetime, timedelta
from itertools import pairwise

import pytest

from app.modules.warehouses.models import DockDirection, DockStatus, EquipmentStatus
from app.modules.yard import rules
from app.modules.yard.rules import DockState, VisitState
from app.modules.yard.simulator import plan_until, plan_visit

T0 = datetime(2026, 10, 7, 12, 0, tzinfo=UTC)
ARRIVES = T0
DOCKED = T0 + timedelta(minutes=4)
DEPARTS = T0 + timedelta(minutes=24)


def state(now: datetime, direction: DockDirection = DockDirection.OUTBOUND) -> VisitState:
    return rules.visit_state(ARRIVES, DOCKED, DEPARTS, direction, now)


@pytest.mark.parametrize(
    ("offset_minutes", "expected"),
    [
        (-10, VisitState.SCHEDULED),
        (-6, VisitState.EN_ROUTE),  # boundary: visible from APPROACH_TIME before arrival
        (-0.1, VisitState.EN_ROUTE),
        (0, VisitState.WAITING),  # boundary: arrival moment
        (3.9, VisitState.WAITING),
        (4, VisitState.DOCKED),  # boundary: starts reversing in
        (4.9, VisitState.DOCKED),
        (5, VisitState.LOADING),  # boundary: DOCKING_TIME over
        (23.9, VisitState.LOADING),
        (24, VisitState.DEPARTED),  # boundary: pulling away
        (25.9, VisitState.DEPARTED),
        (26, VisitState.COMPLETED),
    ],
)
def test_visit_state_boundaries(offset_minutes: float, expected: VisitState) -> None:
    assert state(T0 + timedelta(minutes=offset_minutes)) == expected


def test_inbound_trucks_unload_instead_of_load() -> None:
    working = T0 + timedelta(minutes=10)
    assert state(working, DockDirection.INBOUND) == VisitState.UNLOADING
    assert state(working, DockDirection.OUTBOUND) == VisitState.LOADING


def test_pallets_done_progresses_linearly_and_never_overshoots() -> None:
    work_start = DOCKED + rules.DOCKING_TIME  # 5 min; work lasts 19 min
    assert rules.pallets_done(DOCKED, DEPARTS, 19, work_start) == 0
    assert rules.pallets_done(DOCKED, DEPARTS, 19, DOCKED) == 0  # still reversing in
    assert rules.pallets_done(DOCKED, DEPARTS, 19, work_start + timedelta(minutes=10)) == 10
    assert rules.pallets_done(DOCKED, DEPARTS, 19, DEPARTS) == 19
    assert rules.pallets_done(DOCKED, DEPARTS, 19, DEPARTS + timedelta(hours=1)) == 19


def test_pallets_done_with_no_work_window_counts_as_finished() -> None:
    assert rules.pallets_done(DOCKED, DOCKED, 5, DOCKED + timedelta(minutes=2)) == 5


@pytest.mark.parametrize(
    ("current", "expected"),
    [
        (VisitState.EN_ROUTE, 5),  # until the truck reaches the dock: 4 min + 1 min
        (VisitState.WAITING, 4),
        (VisitState.LOADING, 19),  # until it leaves
        (VisitState.DEPARTED, None),
        (VisitState.SCHEDULED, None),
    ],
)
def test_minutes_remaining_depends_on_the_milestone(
    current: VisitState, expected: int | None
) -> None:
    now = {
        VisitState.EN_ROUTE: T0 - timedelta(minutes=1),
        VisitState.WAITING: T0,
        VisitState.LOADING: T0 + timedelta(minutes=5),
    }.get(current, T0 + timedelta(minutes=25))
    result = rules.minutes_remaining(current, DOCKED, DEPARTS, now)
    assert result == expected


def test_minutes_remaining_rounds_up_and_never_negative() -> None:
    almost = DEPARTS - timedelta(seconds=10)
    assert rules.minutes_remaining(VisitState.LOADING, DOCKED, DEPARTS, almost) == 1
    late = DEPARTS + timedelta(minutes=1)
    assert rules.minutes_remaining(VisitState.LOADING, DOCKED, DEPARTS, late) == 0


@pytest.mark.parametrize(
    ("status", "visit_states", "expected"),
    [
        (DockStatus.OUT_OF_SERVICE, [VisitState.LOADING], DockState.OUT_OF_SERVICE),
        (DockStatus.AVAILABLE, [], DockState.AVAILABLE),
        (DockStatus.AVAILABLE, [VisitState.DEPARTED], DockState.AVAILABLE),
        (DockStatus.AVAILABLE, [VisitState.EN_ROUTE], DockState.BOOKED),
        (DockStatus.AVAILABLE, [VisitState.WAITING], DockState.BOOKED),
        (DockStatus.AVAILABLE, [VisitState.DOCKED], DockState.OCCUPIED),
        (DockStatus.AVAILABLE, [VisitState.UNLOADING, VisitState.WAITING], DockState.OCCUPIED),
    ],
)
def test_dock_state(
    status: DockStatus, visit_states: list[VisitState], expected: DockState
) -> None:
    assert rules.dock_state(status, visit_states) == expected


def test_a_dock_never_gets_more_forklifts_than_it_has_room_for() -> None:
    equipment = [(f"FL-{n:03d}", EquipmentStatus.ACTIVE) for n in range(1, 6)]
    one_dock = rules.assign_equipment(equipment, ["Out 1"])
    assert one_dock == {"FL-001": "Out 1", "FL-002": "Out 1"}
    two_docks = rules.assign_equipment(equipment, ["In 1", "Out 1"])
    assert len(two_docks) == 4
    assert all(list(two_docks.values()).count(d) == 2 for d in ("In 1", "Out 1"))
    assert "FL-005" not in two_docks


def test_only_active_forklifts_are_assigned_and_share_working_docks() -> None:
    equipment = [
        ("FL-003", EquipmentStatus.ACTIVE),
        ("FL-001", EquipmentStatus.ACTIVE),
        ("FL-002", EquipmentStatus.CHARGING),
        ("FL-004", EquipmentStatus.ACTIVE),
        ("FL-005", EquipmentStatus.MAINTENANCE),
    ]
    assert rules.assign_equipment(equipment, ["In 1", "Out 1"]) == {
        "FL-001": "In 1",
        "FL-003": "Out 1",
        "FL-004": "In 1",
    }
    assert rules.assign_equipment(equipment, []) == {}


# --- simulator ------------------------------------------------------------------------------


def test_plan_visit_is_deterministic() -> None:
    a = plan_visit("WH-X", "In 1", 3, T0)
    assert a == plan_visit("WH-X", "In 1", 3, T0)
    assert a != plan_visit("WH-X", "In 1", 4, T0)
    assert a != plan_visit("WH-X", "In 2", 3, T0)


def test_planned_visit_timeline_is_valid() -> None:
    for sequence in range(50):
        visit = plan_visit("WH-X", "Out 2", sequence, T0)
        # A truck may reach the yard before the dock is free, but never reverses in early.
        assert visit.arrives_at < visit.docked_at < visit.departs_at
        assert visit.docked_at > T0
        assert visit.pallets_total > 0
        assert visit.truck_code.startswith("TRK-")


def test_plan_until_chains_visits_without_overlap_and_covers_the_horizon() -> None:
    until = T0 + timedelta(hours=3)
    visits = plan_until("WH-X", "In 1", 5, T0, until)

    assert [v.sequence for v in visits] == list(range(5, 5 + len(visits)))
    assert visits[-1].docked_at < until + timedelta(hours=1)
    for earlier, later in pairwise(visits):
        # The next truck only starts reversing once the previous one has pulled away.
        assert later.docked_at >= earlier.departs_at + rules.LEAVING_TIME


def test_plan_until_adds_nothing_when_already_covered() -> None:
    assert plan_until("WH-X", "In 1", 9, T0 + timedelta(hours=4), T0 + timedelta(hours=3)) == []
