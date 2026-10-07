import logging

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from pydantic import BaseModel

from app.core.config import Settings
from app.core.errors import ConflictError, NotFoundError


class _Payload(BaseModel):
    quantity: int


@pytest.fixture(autouse=True)
def _probe_routes(app: FastAPI) -> None:
    """Test-only endpoints that trigger each error path."""

    @app.post("/_probe/validate")
    async def validate(payload: _Payload) -> dict[str, int]:
        return {"quantity": payload.quantity}

    @app.get("/_probe/not-found")
    async def not_found() -> None:
        raise NotFoundError("Order ORD-1 not found", details={"order_number": "ORD-1"})

    @app.get("/_probe/conflict")
    async def conflict() -> None:
        raise ConflictError("Duplicate order number")

    @app.get("/_probe/boom")
    async def boom() -> None:
        raise RuntimeError("secret internal detail")


async def test_unknown_route_uses_error_envelope(client: AsyncClient) -> None:
    response = await client.get("/api/v1/does-not-exist")

    assert response.status_code == 404
    error = response.json()["error"]
    assert error["code"] == "http_error"
    assert error["request_id"] == response.headers["X-Request-ID"]


async def test_validation_error_is_structured(client: AsyncClient) -> None:
    response = await client.post("/_probe/validate", json={"quantity": "many"})

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "validation_error"
    assert error["details"][0]["location"] == ["body", "quantity"]


async def test_domain_errors_map_to_http_status(client: AsyncClient) -> None:
    not_found = await client.get("/_probe/not-found")
    conflict = await client.get("/_probe/conflict")

    assert not_found.status_code == 404
    assert not_found.json()["error"]["code"] == "not_found"
    assert not_found.json()["error"]["details"] == {"order_number": "ORD-1"}
    assert conflict.status_code == 409


async def test_unhandled_error_does_not_leak_internals(
    client: AsyncClient, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.ERROR):
        response = await client.get("/_probe/boom")

    assert response.status_code == 500
    assert "secret internal detail" not in response.text
    assert response.json()["error"]["code"] == "internal_error"
    assert "secret internal detail" in caplog.text  # but it IS logged server-side


async def test_request_id_is_generated(client: AsyncClient) -> None:
    response = await client.get("/api/v1/health")

    assert len(response.headers["X-Request-ID"]) == 32


async def test_valid_client_request_id_is_echoed(client: AsyncClient) -> None:
    response = await client.get("/api/v1/health", headers={"X-Request-ID": "trace-abc_123"})

    assert response.headers["X-Request-ID"] == "trace-abc_123"


async def test_malicious_request_id_is_replaced(client: AsyncClient) -> None:
    response = await client.get("/api/v1/health", headers={"X-Request-ID": "bad id\nINJECT"})

    assert response.headers["X-Request-ID"] != "bad id\nINJECT"
    assert len(response.headers["X-Request-ID"]) == 32


async def test_cors_allows_configured_origin(client: AsyncClient) -> None:
    response = await client.options(
        "/api/v1/health",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"


async def test_cors_rejects_unknown_origin(client: AsyncClient) -> None:
    response = await client.get("/api/v1/health", headers={"Origin": "http://evil.example"})

    assert "access-control-allow-origin" not in response.headers


def test_cors_origins_parsed_from_comma_separated_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CORS_ORIGINS", "http://a.test, http://b.test")

    parsed = Settings(_env_file=None)

    assert parsed.cors_origins == ["http://a.test", "http://b.test"]
