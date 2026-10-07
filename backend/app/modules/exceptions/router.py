"""HTTP layer for exceptions (operational incidents)."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import DbSession
from app.core.errors import error_responses
from app.core.pagination import Page
from app.modules.exceptions.schemas import ExceptionListParams, ExceptionRead, ExceptionUpdate
from app.modules.exceptions.service import ExceptionService

router = APIRouter(prefix="/exceptions", tags=["exceptions"])


def get_exception_service(session: DbSession) -> ExceptionService:
    return ExceptionService(session)


Service = Annotated[ExceptionService, Depends(get_exception_service)]


@router.get("", response_model=Page[ExceptionRead], summary="List exceptions")
async def list_exceptions(
    params: Annotated[ExceptionListParams, Query()], service: Service
) -> Page[ExceptionRead]:
    return await service.list(params)


@router.get(
    "/{exception_id}",
    response_model=ExceptionRead,
    responses=error_responses(404),
    summary="Get an exception",
)
async def get_exception(exception_id: uuid.UUID, service: Service) -> ExceptionRead:
    return await service.get(exception_id)


@router.patch(
    "/{exception_id}",
    response_model=ExceptionRead,
    responses=error_responses(404, 409, 422),
    summary="Update status / severity; resolving requires a resolution note",
)
async def update_exception(
    exception_id: uuid.UUID, payload: ExceptionUpdate, service: Service
) -> ExceptionRead:
    return await service.update(exception_id, payload)
