"""Exception (incident) workflow rules (pure functions)."""

from app.core.errors import ConflictError
from app.modules.exceptions.models import ExceptionSeverity, ExceptionStatus

ALLOWED_TRANSITIONS: dict[ExceptionStatus, frozenset[ExceptionStatus]] = {
    ExceptionStatus.OPEN: frozenset({ExceptionStatus.INVESTIGATING, ExceptionStatus.RESOLVED}),
    ExceptionStatus.INVESTIGATING: frozenset({ExceptionStatus.RESOLVED}),
    ExceptionStatus.RESOLVED: frozenset(),  # closed incidents are history; raise a new one
}
ACTIVE_STATUSES = frozenset({ExceptionStatus.OPEN, ExceptionStatus.INVESTIGATING})
SEVERITY_RANK = {severity: rank for rank, severity in enumerate(ExceptionSeverity)}


class InvalidExceptionTransitionError(ConflictError):
    code = "invalid_status_transition"


class DuplicateActiveExceptionError(ConflictError):
    code = "duplicate_active_exception"


def ensure_transition_allowed(current: ExceptionStatus, target: ExceptionStatus) -> None:
    if target == current:
        return
    if target not in ALLOWED_TRANSITIONS[current]:
        raise InvalidExceptionTransitionError(
            f"Exception status cannot change from {current} to {target}",
            details={
                "current": current,
                "requested": target,
                "allowed": sorted(ALLOWED_TRANSITIONS[current]),
            },
        )


def higher_severity(a: ExceptionSeverity, b: ExceptionSeverity) -> ExceptionSeverity:
    return a if SEVERITY_RANK[a] >= SEVERITY_RANK[b] else b
