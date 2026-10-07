"""Exception (incident) use cases. Depends on no other module's service."""

import logging
import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import BusinessRuleError, ConflictError, NotFoundError
from app.core.pagination import Page
from app.modules.exceptions import rules
from app.modules.exceptions.models import (
    ExceptionSeverity,
    ExceptionStatus,
    ExceptionType,
    ShipmentException,
)
from app.modules.exceptions.repository import ExceptionRepository, ExceptionRow
from app.modules.exceptions.schemas import ExceptionListParams, ExceptionRead, ExceptionUpdate

logger = logging.getLogger(__name__)


class ExceptionClosedError(ConflictError):
    code = "exception_closed"


def to_read(row: ExceptionRow) -> ExceptionRead:
    exception, shipment_number, warehouse_code, destination = row
    return ExceptionRead(
        id=exception.id,
        shipment_id=exception.shipment_id,
        shipment_number=shipment_number,
        warehouse_code=warehouse_code,
        destination=destination,
        type=exception.type,
        severity=exception.severity,
        status=exception.status,
        description=exception.description,
        created_at=exception.created_at,
        resolved_at=exception.resolved_at,
        resolution_note=exception.resolution_note,
    )


class ExceptionService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.exceptions = ExceptionRepository(session)

    async def list(self, params: ExceptionListParams) -> Page[ExceptionRead]:
        rows, total = await self.exceptions.list(params)
        return Page[ExceptionRead](
            items=[to_read(row) for row in rows],
            total=total,
            limit=params.limit,
            offset=params.offset,
        )

    async def get(self, exception_id: uuid.UUID) -> ExceptionRead:
        row = await self.exceptions.get_row(exception_id)
        if row is None:
            raise NotFoundError(
                f"Exception {exception_id} not found", details={"id": str(exception_id)}
            )
        return to_read(row)

    async def active_for_shipment(self, shipment_id: uuid.UUID) -> Sequence[ExceptionRead]:
        return [to_read(row) for row in await self.exceptions.active_for_shipment(shipment_id)]

    async def read_many(self, ids: Sequence[uuid.UUID]) -> Sequence[ExceptionRead]:
        return [to_read(row) for row in await self.exceptions.rows_by_ids(ids)]

    async def update(self, exception_id: uuid.UUID, data: ExceptionUpdate) -> ExceptionRead:
        exception = await self.exceptions.get(exception_id)
        if exception is None:
            raise NotFoundError(f"Exception {exception_id} not found")
        if exception.status == ExceptionStatus.RESOLVED:
            raise ExceptionClosedError("A resolved exception can no longer be changed")
        if data.status is not None:
            rules.ensure_transition_allowed(exception.status, data.status)

        resolving = data.status == ExceptionStatus.RESOLVED
        note = data.resolution_note or exception.resolution_note
        if resolving and not note:
            raise BusinessRuleError("resolution_note is required to resolve an exception")

        if data.severity is not None:
            exception.severity = data.severity
        if data.resolution_note is not None:
            exception.resolution_note = data.resolution_note
        if data.status is not None:
            exception.status = data.status
        if resolving:
            exception.resolved_at = datetime.now(UTC)
        await self.session.commit()
        logger.info("Exception %s updated: %s", exception.id, sorted(data.model_fields_set))
        return await self.get(exception.id)

    async def raise_new(
        self,
        shipment_id: uuid.UUID,
        kind: ExceptionType,
        severity: ExceptionSeverity,
        description: str,
    ) -> ExceptionRead:
        """Manually raised incident; one active incident per type and shipment."""
        if await self.exceptions.find_active(shipment_id, kind):
            raise rules.DuplicateActiveExceptionError(
                f"An active {kind} exception already exists for this shipment"
            )
        exception = ShipmentException(
            shipment_id=shipment_id, type=kind, severity=severity, description=description
        )
        self.exceptions.add(exception)
        try:
            await self.session.commit()
        except IntegrityError as error:
            # Concurrent request raised the same incident; the partial unique index caught it.
            await self.session.rollback()
            raise rules.DuplicateActiveExceptionError(
                f"An active {kind} exception already exists for this shipment"
            ) from error
        return await self.get(exception.id)

    async def raise_or_escalate(
        self,
        shipment_id: uuid.UUID,
        kind: ExceptionType,
        severity: ExceptionSeverity,
        description: str,
    ) -> ShipmentException:
        """Used by automatic detection (e.g. tracking events). Does not commit: the caller owns
        the transaction. Repeated signals update the active incident instead of duplicating it.
        """
        active = await self.exceptions.find_active(shipment_id, kind)
        if active is not None:
            active.severity = rules.higher_severity(active.severity, severity)
            active.description = description
            return active
        exception = ShipmentException(
            id=uuid.uuid4(),
            shipment_id=shipment_id,
            type=kind,
            severity=severity,
            description=description,
            status=ExceptionStatus.OPEN,
        )
        self.exceptions.add(exception)
        return exception
