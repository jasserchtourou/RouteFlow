"""The `python -m app.seed` command, end to end against the test database.

It commits real data (unlike the other tests), so the fixture wipes every table afterwards;
otherwise tests that expect an empty database would fail depending on execution order.
"""

from collections.abc import AsyncIterator

import pytest
from sqlalchemy import func, select

from app.core.config import Settings
from app.modules.shipments.models import Shipment
from app.seed import __main__ as seed_cli
from app.seed.runner import reset_database
from tests.db.conftest import SessionFactory


@pytest.fixture
async def seeded_cli(
    monkeypatch: pytest.MonkeyPatch, session_factory: SessionFactory, test_database_url: str
) -> AsyncIterator[None]:
    settings = Settings(_env_file=None, database_url=test_database_url)
    monkeypatch.setattr(seed_cli, "get_settings", lambda: settings)
    yield
    async with session_factory() as session:  # leave the database empty for other tests
        await reset_database(session)
        await session.commit()


async def _shipment_count(session_factory: SessionFactory) -> int:
    async with session_factory() as session:
        return await session.scalar(select(func.count()).select_from(Shipment)) or 0


@pytest.mark.usefixtures("seeded_cli")
async def test_cli_seeds_refuses_to_overwrite_and_resets(
    session_factory: SessionFactory, capsys: pytest.CaptureFixture[str]
) -> None:
    assert await seed_cli.main(reset=False, seed=7) == 0
    assert "Seeded 7 warehouses" in capsys.readouterr().out
    first_count = await _shipment_count(session_factory)
    assert first_count > 0

    assert await seed_cli.main(reset=False, seed=7) == 1  # non-empty: refuses, exit code 1
    assert "already contains data" in capsys.readouterr().out
    assert await _shipment_count(session_factory) == first_count  # nothing was touched

    assert await seed_cli.main(reset=True, seed=8) == 0  # --reset replaces the data
    assert await _shipment_count(session_factory) == first_count
