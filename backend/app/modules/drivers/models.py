from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, enum_checks, enum_column

if TYPE_CHECKING:
    from app.modules.vehicles.models import Vehicle


class DriverStatus(StrEnum):
    AVAILABLE = "AVAILABLE"
    ON_DUTY = "ON_DUTY"
    OFF_DUTY = "OFF_DUTY"


class Driver(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "drivers"
    __table_args__ = (*enum_checks(status=DriverStatus),)

    full_name: Mapped[str] = mapped_column(String(120))
    license_number: Mapped[str] = mapped_column(String(32), unique=True)
    phone: Mapped[str | None] = mapped_column(String(32))
    status: Mapped[DriverStatus] = mapped_column(
        enum_column(DriverStatus, "driver_status"), default=DriverStatus.AVAILABLE
    )

    vehicle: Mapped[Vehicle | None] = relationship(back_populates="driver", lazy="raise")
