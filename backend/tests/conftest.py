"""Shared fixtures.

Two kinds of tests:
- fast tests that never touch PostgreSQL (`app`, `client`);
- integration tests that use the real database (`session`, `db_client`). The schema is built by
  running the actual Alembic migrations once per test session, and each test runs inside a
  transaction that is rolled back, so tests are isolated and leave no data behind.
"""

import asyncio
from collections.abc import AsyncIterator

import asyncpg
import pytest
from alembic.config import Config
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import make_url
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession, create_async_engine

from alembic import command
from app.core.config import Settings, get_settings
from app.core.database import get_session
from app.main import create_app


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Any test that needs PostgreSQL is marked `integration` (skip with -m "not integration")."""
    for item in items:
        if "test_database_url" in getattr(item, "fixturenames", ()):
            item.add_marker(pytest.mark.integration)


# --- application ----------------------------------------------------------------------------


@pytest.fixture
def settings() -> Settings:
    # Explicit settings: tests never depend on the developer's local .env.
    return Settings(
        _env_file=None,
        app_env="test",
        log_level="WARNING",
        cors_origins=["http://localhost:3000"],
    )


@pytest.fixture
async def app(settings: Settings) -> AsyncIterator[FastAPI]:
    application = create_app(settings)
    # httpx's ASGITransport does not run lifespan events, so run them explicitly.
    async with application.router.lifespan_context(application):
        yield application


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    # raise_app_exceptions=False: behave like a real server and return the 500 response
    # instead of re-raising the exception into the test.
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as http_client:
        yield http_client


# --- database -------------------------------------------------------------------------------


def _asyncpg_dsn(url: str) -> str:
    return make_url(url).set(drivername="postgresql").render_as_string(hide_password=False)


async def _recreate_database(url: str) -> None:
    """Drop and create the test database, so every run starts from nothing."""
    parsed = make_url(url)
    database = parsed.database
    # A real exception, not `assert`: asserts vanish under `python -O`, and this guards a DROP.
    if not database or not database.endswith("_test"):
        raise RuntimeError(f"Refusing to wipe {database!r}: test database names must end in _test")
    maintenance_url = parsed.set(database="postgres").render_as_string(hide_password=False)
    admin = await asyncpg.connect(_asyncpg_dsn(maintenance_url))
    try:
        await admin.execute(f'DROP DATABASE IF EXISTS "{database}" WITH (FORCE)')
        await admin.execute(f'CREATE DATABASE "{database}"')
    finally:
        await admin.close()


@pytest.fixture(scope="session")
def test_database_url() -> str:
    url = get_settings().test_database_url
    asyncio.run(_recreate_database(url))
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", url)
    command.upgrade(config, "head")
    return url


@pytest.fixture
async def connection(test_database_url: str) -> AsyncIterator[AsyncConnection]:
    engine = create_async_engine(test_database_url)
    async with engine.connect() as conn:
        transaction = await conn.begin()
        yield conn
        await transaction.rollback()
    await engine.dispose()


@pytest.fixture
async def session(connection: AsyncConnection) -> AsyncIterator[AsyncSession]:
    # create_savepoint: code under test may call commit()/rollback(); they only affect a
    # SAVEPOINT, and the outer transaction is still rolled back at the end of the test.
    async with AsyncSession(
        bind=connection, join_transaction_mode="create_savepoint", expire_on_commit=False
    ) as db_session:
        yield db_session


@pytest.fixture
async def db_client(app: FastAPI, session: AsyncSession) -> AsyncIterator[AsyncClient]:
    """HTTP client whose requests all use the test's rolled-back session."""

    async def override() -> AsyncIterator[AsyncSession]:
        yield session

    app.dependency_overrides[get_session] = override
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as http_client:
        yield http_client
    app.dependency_overrides.clear()
