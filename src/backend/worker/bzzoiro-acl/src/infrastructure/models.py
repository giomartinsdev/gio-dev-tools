from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Engine, String, UniqueConstraint, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

SCHEMA = "bzzoiro_data"


class Base(DeclarativeBase):
    pass


class ProviderMappingModel(Base):
    __tablename__ = "provider_mappings"
    __table_args__ = (
        UniqueConstraint("provider", "provider_ref", "entity_type", name="uq_provider_mapping"),
        {"schema": SCHEMA},
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    provider: Mapped[str] = mapped_column(String, nullable=False)
    provider_ref: Mapped[str] = mapped_column(String, nullable=False)
    entity_type: Mapped[str] = mapped_column(String, nullable=False)
    canonical_id: Mapped[str] = mapped_column(String, nullable=False)


class SyncCheckpointModel(Base):
    """Owned entirely by bzzoiro-acl: tracks how far each poll loop has
    gotten, so a restart resumes instead of re-fetching from scratch. Not to
    be confused with domain-persister's read models — this is the ACL's own
    polling state, never read/written by any other service."""

    __tablename__ = "sync_checkpoints"
    __table_args__ = ({"schema": SCHEMA},)

    feed_type: Mapped[str] = mapped_column(String, primary_key=True)
    cursor: Mapped[str] = mapped_column(String, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow,
    )


def create_all(engine: Engine) -> None:
    """Create the bzzoiro_data schema (Postgres doesn't do this for us) then the tables in it."""
    with engine.begin() as conn:
        conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}"))
    Base.metadata.create_all(engine)
