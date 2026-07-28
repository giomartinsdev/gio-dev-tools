from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, Integer, String, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from shared.timezone_handler import TimezoneAware

_SP = TimezoneAware("America/Sao_Paulo")


class Base(DeclarativeBase):
    pass


class TrackedLineModel(Base):
    __tablename__ = "tracked_lines"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    line_code: Mapped[str] = mapped_column(String, nullable=False, index=True)
    mode: Mapped[str] = mapped_column(String, nullable=False, default="sppo")
    label: Mapped[Optional[str]] = mapped_column(String, nullable=True, default=None)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: _SP.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: _SP.now, onupdate=lambda: _SP.now)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, default=None)


class BusDirectionModel(Base):
    __tablename__ = "bus_directions"
    __table_args__ = (
        UniqueConstraint("mode", "line_code", "direction_id", name="uq_bus_direction_mode_line_direction"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    mode: Mapped[str] = mapped_column(String, nullable=False)
    line_code: Mapped[str] = mapped_column(String, nullable=False, index=True)
    direction_id: Mapped[int] = mapped_column(Integer, nullable=False)
    headsign: Mapped[Optional[str]] = mapped_column(String, nullable=True, default=None)


class BusStopModel(Base):
    __tablename__ = "bus_stops"
    __table_args__ = (
        UniqueConstraint("mode", "line_code", "direction_id", "stop_id", name="uq_bus_stop_mode_line_direction_stop"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    mode: Mapped[str] = mapped_column(String, nullable=False)
    line_code: Mapped[str] = mapped_column(String, nullable=False, index=True)
    direction_id: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    stop_id: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[Optional[str]] = mapped_column(String, nullable=True, default=None)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)


class BusShapePointModel(Base):
    __tablename__ = "bus_shape_points"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    mode: Mapped[str] = mapped_column(String, nullable=False)
    line_code: Mapped[str] = mapped_column(String, nullable=False, index=True)
    direction_id: Mapped[int] = mapped_column(Integer, nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)


class BusPositionModel(Base):
    __tablename__ = "bus_positions"
    __table_args__ = (
        UniqueConstraint("vehicle_id", "captured_at", name="uq_bus_position_vehicle_captured"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    mode: Mapped[str] = mapped_column(String, nullable=False, default="sppo")
    line_code: Mapped[str] = mapped_column(String, nullable=False, index=True)
    vehicle_id: Mapped[str] = mapped_column(String, nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    speed_kmh: Mapped[float] = mapped_column(Float, nullable=False)
    color_hex: Mapped[Optional[str]] = mapped_column(String, nullable=True, default=None)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: _SP.now)
