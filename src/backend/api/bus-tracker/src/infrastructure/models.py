from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, String, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from shared.timezone_handler import TimezoneAware

_SP = TimezoneAware("America/Sao_Paulo")


class Base(DeclarativeBase):
    pass


class TrackedLineModel(Base):
    __tablename__ = "tracked_lines"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    line_code: Mapped[str] = mapped_column(String, nullable=False, index=True)
    label: Mapped[Optional[str]] = mapped_column(String, nullable=True, default=None)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: _SP.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: _SP.now, onupdate=lambda: _SP.now)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, default=None)


class BusPositionModel(Base):
    __tablename__ = "bus_positions"
    __table_args__ = (
        UniqueConstraint("vehicle_id", "captured_at", name="uq_bus_position_vehicle_captured"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    line_code: Mapped[str] = mapped_column(String, nullable=False, index=True)
    vehicle_id: Mapped[str] = mapped_column(String, nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    speed_kmh: Mapped[float] = mapped_column(Float, nullable=False)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: _SP.now)
