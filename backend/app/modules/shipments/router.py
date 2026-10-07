"""HTTP layer for shipments."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.dependencies import DbSession
from app.core.errors import error_responses
from app.core.pagination import Page
from app.modules.exceptions.schemas import ExceptionCreate, ExceptionRead
from app.modules.shipments.schemas import ShipmentDetail, ShipmentListParams, ShipmentRead
from app.modules.shipments.service import ShipmentService

router = APIRouter(prefix="/shipments", tags=["shipments"])


def get_shipment_service(session: DbSession) -> ShipmentService:
    return ShipmentService(session)


Service = Annotated[ShipmentService, Depends(get_shipment_service)]


@router.get("", response_model=Page[ShipmentRead], summary="List shipments")
async def list_shipments(
    params: Annotated[ShipmentListParams, Query()], service: Service
) -> Page[ShipmentRead]:
    return await service.list(params)


@router.get(
    "/by-number/{shipment_number}",
    response_model=ShipmentDetail,
    responses=error_responses(404),
    summary="Shipment details by number (e.g. SHP-2211)",
)
async def get_shipment_by_number(shipment_number: str, service: Service) -> ShipmentDetail:
    return await service.detail_by_number(shipment_number)


@router.get(
    "/{shipment_id}",
    response_model=ShipmentDetail,
    responses=error_responses(404),
    summary="Shipment details with latest event and active exceptions",
)
async def get_shipment(shipment_id: uuid.UUID, service: Service) -> ShipmentDetail:
    return await service.detail(shipment_id)


@router.post(
    "/{shipment_id}/exceptions",
    response_model=ExceptionRead,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(404, 409),
    summary="Raise an exception (incident) on a shipment",
)
async def raise_exception(
    shipment_id: uuid.UUID, payload: ExceptionCreate, service: Service
) -> ExceptionRead:
    return await service.raise_exception(shipment_id, payload)
