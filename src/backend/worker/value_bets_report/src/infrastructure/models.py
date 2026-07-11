from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Engine, Integer, String
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class ReportConfigModel(Base):
    """Single-row config table — id is always 1. No multi-report-type
    generalization: this worker only ever sends one report."""

    __tablename__ = "value_bets_report_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    send_time: Mapped[str] = mapped_column(String, nullable=False, default="00:00")
    reference_day_offset: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow,
    )


class RecipientModel(Base):
    __tablename__ = "recipients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    phone_number: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)


def create_all(engine: Engine) -> None:
    Base.metadata.create_all(engine)
    stmt = pg_insert(ReportConfigModel).values(id=1).on_conflict_do_nothing(index_elements=["id"])
    with engine.begin() as conn:
        conn.execute(stmt)
