from datetime import UTC, datetime

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

import app.models  # noqa: F401  (registers all tables)
from app.core.base import Base
from app.modules.warehouses.models import Warehouse
from app.seed.generator import SeedData, generate


class DatabaseNotEmptyError(RuntimeError):
    pass


async def reset_database(session: AsyncSession) -> None:
    """Remove all application data (schema and alembic_version are untouched)."""
    tables = ", ".join(f'"{table.name}"' for table in Base.metadata.sorted_tables)
    await session.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))


async def seed_database(
    session: AsyncSession,
    *,
    now: datetime | None = None,
    seed: int = 42,
    reset: bool = False,
) -> SeedData:
    """Populate the database in a single transaction (all-or-nothing)."""
    if reset:
        await reset_database(session)
    elif await session.scalar(select(func.count()).select_from(Warehouse)):
        raise DatabaseNotEmptyError("Database already contains data; use --reset to replace it.")

    data = generate(now or datetime.now(UTC), seed)
    session.add_all(data.all_objects())
    await session.commit()
    return data
