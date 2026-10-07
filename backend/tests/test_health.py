from collections.abc import AsyncIterator

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.core.config import get_settings
from app.core.database import get_session
from app.main import create_app


class _FakeSession:
    def __init__(self, *, fail: bool) -> None:
        self.fail = fail

    async def execute(self, *_: object, **__: object) -> None:
        if self.fail:
            raise ConnectionRefusedError("db down")


def _override_session(app: FastAPI, *, fail: bool) -> None:
    async def fake() -> AsyncIterator[_FakeSession]:
        yield _FakeSession(fail=fail)

    app.dependency_overrides[get_session] = fake


async def test_health_returns_ok(client: AsyncClient) -> None:
    response = await client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_health_does_not_require_database(client: AsyncClient, app: FastAPI) -> None:
    _override_session(app, fail=True)

    assert (await client.get("/api/v1/health")).status_code == 200


async def test_readiness_ok_when_database_reachable(client: AsyncClient, app: FastAPI) -> None:
    _override_session(app, fail=False)

    response = await client.get("/api/v1/health/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "up"}


async def test_readiness_503_when_database_down(client: AsyncClient, app: FastAPI) -> None:
    _override_session(app, fail=True)

    response = await client.get("/api/v1/health/ready")

    assert response.status_code == 503
    assert response.json() == {"status": "unavailable", "database": "down"}


@pytest.mark.integration
async def test_readiness_against_real_postgres() -> None:
    """Needs `docker compose up -d postgres`; uses the real settings from .env."""
    application = create_app(get_settings())
    transport = ASGITransport(app=application)
    async with (
        application.router.lifespan_context(application),
        AsyncClient(transport=transport, base_url="http://test") as real_client,
    ):
        response = await real_client.get("/api/v1/health/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "up"}
