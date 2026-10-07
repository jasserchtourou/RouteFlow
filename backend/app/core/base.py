import uuid
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import CheckConstraint, DateTime, Enum, MetaData, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Deterministic constraint/index names. Without this, PostgreSQL invents names and Alembic
# cannot reliably drop or alter constraints later.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Declarative base shared by every model; its metadata is what Alembic diffs against."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)
    # Fetch server-generated values (created_at, updated_at via onupdate=now()) in the same
    # INSERT/UPDATE ... RETURNING statement. Otherwise SQLAlchemy expires them after a flush and
    # the next read needs an implicit lazy load, which async SQLAlchemy forbids (MissingGreenlet).
    __mapper_args__ = {"eager_defaults": True}  # noqa: RUF012


class UUIDPrimaryKeyMixin:
    """UUID primary key. Generated in Python (so new objects have an id before flush) and
    by the database (so raw SQL inserts and seed scripts work too)."""

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, server_default=func.gen_random_uuid()
    )


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


def enum_column(enum_class: type[PyEnum], name: str) -> Enum:
    """Enum stored as VARCHAR instead of a native PostgreSQL ENUM.

    Adding a value later is a simple constraint change; ALTER TYPE ... ADD VALUE is awkward
    inside transactions and a value can never be removed. The type only converts between
    Python enums and strings; validity is enforced by `enum_checks` (below), one explicit
    CHECK per column. (Letting the Enum type create its own constraint produces duplicate
    constraints once a naming convention is active.)
    """
    return Enum(enum_class, name=name, native_enum=False, create_constraint=False, length=32)


def enum_checks(**columns: type[PyEnum]) -> tuple[CheckConstraint, ...]:
    """CHECK constraints restricting each named column to its enum's values."""
    return tuple(
        CheckConstraint(
            f"{column} IN ({', '.join(repr(member.value) for member in enum_class)})",
            name=f"{column}_valid",
        )
        for column, enum_class in columns.items()
    )
