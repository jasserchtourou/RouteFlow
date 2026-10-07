import logging
from typing import Literal

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import text

from app.api.dependencies import DbSession

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/health", tags=["health"])


class HealthResponse(BaseModel):
    status: Literal["ok"]


class ReadinessResponse(BaseModel):
    status: Literal["ok", "unavailable"]
    database: Literal["up", "down"]


@router.get("", response_model=HealthResponse, summary="Liveness probe")
async def health() -> HealthResponse:
    """Is the process running? Deliberately does not touch the database."""
    return HealthResponse(status="ok")


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    responses={503: {"model": ReadinessResponse}},
    summary="Readiness probe",
)
async def readiness(session: DbSession) -> ReadinessResponse | JSONResponse:
    """Can the service do useful work? Verifies the database connection."""
    try:
        await session.execute(text("SELECT 1"))
    except Exception:
        logger.exception("Readiness check failed: database unreachable")
        body = ReadinessResponse(status="unavailable", database="down")
        return JSONResponse(status_code=503, content=body.model_dump())
    return ReadinessResponse(status="ok", database="up")
