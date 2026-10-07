"""Reusable query building blocks for repositories: search, whitelisted sorting, pagination."""

from collections.abc import Mapping, Sequence
from typing import Any

from sqlalchemy import ColumnElement, Row, Select, SQLColumnExpression, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import PageParams

# Columns, ORM attributes and hybrid properties all qualify.
Column = SQLColumnExpression[Any]


def escape_like(term: str) -> str:
    """Treat user input literally inside LIKE patterns (`%` and `_` are wildcards)."""
    return term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def contains_any(term: str, *columns: Column) -> ColumnElement[bool]:
    """Case-insensitive substring match of `term` in any of the columns."""
    pattern = f"%{escape_like(term)}%"
    return or_(*(column.ilike(pattern, escape="\\") for column in columns))


def apply_sort[*Ts](
    query: Select[*Ts], sort_key: str, columns: Mapping[str, Column], tiebreaker: Column
) -> Select[*Ts]:
    """Order by a whitelisted key ("name" ascending, "-name" descending).

    NULLs always sort last, and the tie-breaker (a unique column) makes the order total, so
    rows cannot jump between pages when several share the same sort value.
    """
    descending = sort_key.startswith("-")
    column = columns[sort_key.lstrip("-")]
    ordered = column.desc() if descending else column.asc()
    return query.order_by(ordered.nulls_last(), tiebreaker)


async def paginate[T](
    session: AsyncSession, query: Select[T], params: PageParams
) -> tuple[Sequence[T], int]:
    """Run `query` for one page and count all matching rows (ordering is ignored for the count)."""
    total = await session.scalar(select(func.count()).select_from(query.order_by(None).subquery()))
    page = await session.execute(query.limit(params.limit).offset(params.offset))
    return page.scalars().all(), total or 0


async def paginate_rows[*Ts](
    session: AsyncSession, query: Select[*Ts], params: PageParams
) -> tuple[Sequence[Row[*Ts]], int]:
    """Like `paginate`, for queries that select several columns (e.g. an entity + aggregates)."""
    total = await session.scalar(select(func.count()).select_from(query.order_by(None).subquery()))
    page = await session.execute(query.limit(params.limit).offset(params.offset))
    return page.all(), total or 0
