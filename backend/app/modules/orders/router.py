"""HTTP layer for orders: translate requests to service calls. No business logic here."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, Response, status

from app.api.dependencies import DbSession
from app.core.errors import error_responses
from app.core.pagination import Page
from app.modules.orders.schemas import OrderCreate, OrderListParams, OrderRead, OrderUpdate
from app.modules.orders.service import OrderService

router = APIRouter(prefix="/orders", tags=["orders"])


def get_order_service(session: DbSession) -> OrderService:
    return OrderService(session)


Service = Annotated[OrderService, Depends(get_order_service)]


@router.post(
    "",
    response_model=OrderRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create an order",
)
async def create_order(
    payload: OrderCreate, service: Service, request: Request, response: Response
) -> OrderRead:
    order = await service.create(payload)
    response.headers["Location"] = str(request.url_for("get_order", order_id=order.id))
    return OrderRead.model_validate(order)


@router.get("", response_model=Page[OrderRead], summary="List orders")
async def list_orders(
    params: Annotated[OrderListParams, Query()], service: Service
) -> Page[OrderRead]:
    return await service.list(params)


@router.get(
    "/by-number/{order_number}",
    response_model=OrderRead,
    responses=error_responses(404),
    summary="Get an order by its order number (e.g. ORD-10011)",
)
async def get_order_by_number(order_number: str, service: Service) -> OrderRead:
    return OrderRead.model_validate(await service.get_by_number(order_number))


@router.get(
    "/{order_id}", response_model=OrderRead, responses=error_responses(404), summary="Get an order"
)
async def get_order(order_id: uuid.UUID, service: Service) -> OrderRead:
    return OrderRead.model_validate(await service.get(order_id))


@router.patch(
    "/{order_id}",
    response_model=OrderRead,
    responses=error_responses(404, 409),
    summary="Partially update an order",
)
async def update_order(order_id: uuid.UUID, payload: OrderUpdate, service: Service) -> OrderRead:
    return OrderRead.model_validate(await service.update(order_id, payload))


@router.delete(
    "/{order_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=error_responses(404, 409),
    summary="Delete an order without shipments",
)
async def delete_order(order_id: uuid.UUID, service: Service) -> None:
    await service.delete(order_id)
