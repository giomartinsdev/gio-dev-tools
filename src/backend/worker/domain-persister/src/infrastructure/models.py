from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import DateTime, Engine, Integer, MetaData, Numeric, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

SCHEMA = "bzzoiro_data"


class Base(DeclarativeBase):
    metadata = MetaData(schema=SCHEMA)


class EventStoreModel(Base):
    """Append-only store of raw feed envelopes, keyed by event_id for idempotent replay."""

    __tablename__ = "event_store"

    event_id: Mapped[str] = mapped_column(String, primary_key=True)
    event_type: Mapped[str] = mapped_column(String, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)


class MatchModel(Base):
    """Read model materialized from domain.events. Only carries the ids/fields the
    canonical events actually contain — no separate teams/competitions tables, since
    those events never carry team/competition attributes beyond their canonical id."""

    __tablename__ = "matches"

    match_id: Mapped[str] = mapped_column(String, primary_key=True)
    competition_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    home_team_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    away_team_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    status: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    home_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    away_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    minute: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    kickoff_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    venue: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    statistics: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow,
    )


class OddsSnapshotModel(Base):
    __tablename__ = "odds_snapshots"

    id: Mapped[str] = mapped_column(String, primary_key=True)  # source event_id, keeps redelivery idempotent
    match_id: Mapped[str] = mapped_column(String, nullable=False)
    bookmaker: Mapped[str] = mapped_column(String, nullable=False)
    market: Mapped[str] = mapped_column(String, nullable=False)
    selections: Mapped[dict] = mapped_column(JSONB, nullable=False)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class InsightModel(Base):
    """Read model materialized from analysis.events (q.insight.projector).
    Each row is a point-in-time ML prediction — never overwritten, only
    inserted once per insight_id (redelivery is a no-op)."""

    __tablename__ = "insights"

    id: Mapped[str] = mapped_column(String, primary_key=True)  # insight_id, keeps redelivery idempotent
    match_id: Mapped[str] = mapped_column(String, nullable=False)
    market: Mapped[str] = mapped_column(String, nullable=False)
    recommendation: Mapped[str] = mapped_column(String, nullable=False)
    confidence: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    rationale: Mapped[str] = mapped_column(String, nullable=False)
    model: Mapped[str] = mapped_column(String, nullable=False)
    feature_snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


def create_all(engine: Engine) -> None:
    """Create the bzzoiro_data schema (Postgres doesn't do this for us) then the tables in it."""
    with engine.begin() as conn:
        conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}"))
    Base.metadata.create_all(engine)
