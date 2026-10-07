"""HTTP layer for routes."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import DbSession
from app.core.errors import error_responses
from app.core.pagination import Page
from app.modules.routes.schemas import AtRiskParams, RouteDetail, RouteListParams, RouteRead
from app.modules.routes.service import RouteService

router = APIRouter(prefix="/routes", tags=["routes"])


def get_route_service(session: DbSession) -> RouteService:
    return RouteService(session)


Service = Annotated[RouteService, Depends(get_route_service)]


@router.get("", response_model=Page[RouteRead], summary="List routes with live statistics")
async def list_routes(
    params: Annotated[RouteListParams, Query()], service: Service
) -> Page[RouteRead]:
    return await service.list(params)


@router.get(
    "/at-risk",
    response_model=list[RouteRead],
    summary="Routes ranked by computed risk score (what to investigate first)",
)
async def routes_at_risk(
    params: Annotated[AtRiskParams, Query()], service: Service
) -> list[RouteRead]:
    return list(await service.at_risk(params))


@router.get(
    "/by-number/{route_number}",
    response_model=RouteDetail,
    responses=error_responses(404),
    summary="Route details by number (e.g. RTE-110)",
)
async def get_route_by_number(route_number: str, service: Service) -> RouteDetail:
    return await service.detail_by_number(route_number)


@router.get(
    "/{route_id}",
    response_model=RouteDetail,
    responses=error_responses(404),
    summary="Route details with risk assessment and active shipments",
)
async def get_route(route_id: uuid.UUID, service: Service) -> RouteDetail:
    return await service.detail(route_id)
