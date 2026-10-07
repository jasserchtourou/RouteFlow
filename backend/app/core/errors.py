import logging
from typing import Any, cast

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


class AppError(Exception):
    """Base class for expected, domain-level errors.

    Services raise these; the handlers below translate them into HTTP responses,
    so business code never imports HTTP concepts.
    """

    status_code = 400
    code = "app_error"

    def __init__(self, message: str, *, details: Any = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details


class NotFoundError(AppError):
    status_code = 404
    code = "not_found"


class ConflictError(AppError):
    status_code = 409
    code = "conflict"


class BusinessRuleError(AppError):
    status_code = 422
    code = "business_rule_violation"


class ErrorBody(BaseModel):
    code: str
    message: str
    details: Any = None
    request_id: str | None = None


class ErrorResponse(BaseModel):
    """Documents the error envelope in OpenAPI (`responses={404: {"model": ErrorResponse}}`)."""

    error: ErrorBody


_ERROR_DESCRIPTIONS = {
    404: "Resource not found",
    409: "Conflicts with the current state of the resource (business rule)",
    422: "Request validation failed or business rule violated",
}


def error_responses(*status_codes: int) -> dict[int | str, dict[str, Any]]:
    """OpenAPI `responses=` entry documenting the error envelope for the given status codes."""
    return {
        code: {"model": ErrorResponse, "description": _ERROR_DESCRIPTIONS.get(code, "Error")}
        for code in status_codes
    }


def error_response(
    request: Request, status_code: int, code: str, message: str, details: Any = None
) -> JSONResponse:
    """Every error leaves the API in this single envelope."""
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "details": details,
                "request_id": getattr(request.state, "request_id", None),
            }
        },
    )


async def _app_error_handler(request: Request, exc: Exception) -> JSONResponse:
    exc = cast("AppError", exc)
    return error_response(request, exc.status_code, exc.code, exc.message, exc.details)


async def _http_error_handler(request: Request, exc: Exception) -> JSONResponse:
    exc = cast("StarletteHTTPException", exc)
    return error_response(request, exc.status_code, "http_error", str(exc.detail))


async def _validation_error_handler(request: Request, exc: Exception) -> JSONResponse:
    exc = cast("RequestValidationError", exc)
    details = [
        {"location": list(err["loc"]), "message": err["msg"], "type": err["type"]}
        for err in exc.errors()
    ]
    return error_response(request, 422, "validation_error", "Request validation failed", details)


async def _unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    # Log the full traceback server-side; never leak internals to the client.
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return error_response(request, 500, "internal_error", "Internal server error")


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, _app_error_handler)
    app.add_exception_handler(StarletteHTTPException, _http_error_handler)
    app.add_exception_handler(RequestValidationError, _validation_error_handler)
    app.add_exception_handler(Exception, _unhandled_error_handler)
