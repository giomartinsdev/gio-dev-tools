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


class TeamModel(Base):
    __tablename__ = "teams"

    team_id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    short_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    country: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    venue_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow,
    )


class SquadMemberModel(Base):
    __tablename__ = "squad_members"

    squad_row_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    team_id: Mapped[str] = mapped_column(String, nullable=False)
    player_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    jersey_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    position: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    club: Mapped[str] = mapped_column(String, nullable=False)
    club_country: Mapped[str] = mapped_column(String, nullable=False)
    caps: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    goals: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    age: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    date_of_birth: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow,
    )



class OddsComparisonModel(Base):
    """Latest known odds-comparison snapshot per match — overwritten on each
    poll (not append-only) since only the current picture matters for
    value-bet detection. `markets` is the verbatim per-market/per-outcome/
    per-bookmaker breakdown, including each outcome's precomputed best price."""

    __tablename__ = "odds_comparisons"

    match_id: Mapped[str] = mapped_column(String, primary_key=True)
    bookmakers_count: Mapped[int] = mapped_column(Integer, nullable=False)
    total_odds: Mapped[int] = mapped_column(Integer, nullable=False)
    markets: Mapped[dict] = mapped_column(JSONB, nullable=False)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class PolymarketSnapshotModel(Base):
    """Latest known Polymarket snapshot per match — same "current state,
    overwritten" semantics as OddsComparisonModel. Kept for cross-checking
    against bookmaker odds and bzzoiro's own model, even though no live
    example ever populated this while the ingestion was written."""

    __tablename__ = "polymarket_snapshots"

    match_id: Mapped[str] = mapped_column(String, primary_key=True)
    markets: Mapped[dict] = mapped_column(JSONB, nullable=False)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ValueBetModel(Base):
    """A detected edge between bzzoiro's model probability and the best
    market price for one (match, market, outcome). Upserted keyed by that
    triple — this is "the current known opportunity", not a growing history
    of every time it was recomputed. Deleted outright once the edge drops
    back below the threshold (see ValueBetDetector)."""

    __tablename__ = "value_bets"

    match_id: Mapped[str] = mapped_column(String, primary_key=True)
    market: Mapped[str] = mapped_column(String, primary_key=True)
    outcome: Mapped[str] = mapped_column(String, primary_key=True)
    model_probability: Mapped[Decimal] = mapped_column(Numeric(6, 5), nullable=False)
    bookmaker: Mapped[str] = mapped_column(String, nullable=False)
    best_odds: Mapped[Decimal] = mapped_column(Numeric(8, 3), nullable=False)
    implied_probability: Mapped[Decimal] = mapped_column(Numeric(6, 5), nullable=False)
    edge: Mapped[Decimal] = mapped_column(Numeric(6, 5), nullable=False)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


def create_all(engine: Engine) -> None:
    """Create the bzzoiro_data schema (Postgres doesn't do this for us) then the tables in it."""
    with engine.begin() as conn:
        conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}"))
    Base.metadata.create_all(engine)
