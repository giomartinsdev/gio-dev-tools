from __future__ import annotations

from sqlalchemy import Engine, String, UniqueConstraint, text
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


def create_all(engine: Engine) -> None:
    """Create the bzzoiro_data schema (Postgres doesn't do this for us) then the tables in it."""
    with engine.begin() as conn:
        conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}"))
    Base.metadata.create_all(engine)
