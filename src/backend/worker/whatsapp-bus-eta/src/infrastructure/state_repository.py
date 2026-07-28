from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Float, String
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from shared.timezone_handler import TimezoneAware
from shared.transaction_manager import TransactionManager

from ..domain.conversation_state import ConversationState
from ..domain.repository import ConversationStateRepository

_SP = TimezoneAware("America/Sao_Paulo")


class Base(DeclarativeBase):
    pass


class ConversationStateModel(Base):
    __tablename__ = "whatsapp_bus_eta_state"

    remote_jid: Mapped[str] = mapped_column(String, primary_key=True)
    lat: Mapped[Optional[float]] = mapped_column(Float, nullable=True, default=None)
    lon: Mapped[Optional[float]] = mapped_column(Float, nullable=True, default=None)
    mode: Mapped[Optional[str]] = mapped_column(String, nullable=True, default=None)
    line_code: Mapped[Optional[str]] = mapped_column(String, nullable=True, default=None)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: _SP.now, onupdate=lambda: _SP.now,
    )


class PostgresConversationStateRepository(ConversationStateRepository):
    def get(self, remote_jid: str) -> ConversationState:
        with TransactionManager.get().read_only() as s:
            row = s.get(ConversationStateModel, remote_jid)
            if row is None:
                return ConversationState(remote_jid=remote_jid)
            return ConversationState(
                remote_jid=remote_jid, lat=row.lat, lon=row.lon, mode=row.mode, line_code=row.line_code,
            )

    def set_location(self, remote_jid: str, lat: float, lon: float) -> None:
        stmt = pg_insert(ConversationStateModel).values(
            remote_jid=remote_jid, lat=lat, lon=lon,
        ).on_conflict_do_update(
            index_elements=["remote_jid"], set_={"lat": lat, "lon": lon},
        )
        with TransactionManager.get().session() as s:
            s.execute(stmt)

    def set_line(self, remote_jid: str, mode: str, line_code: str) -> None:
        stmt = pg_insert(ConversationStateModel).values(
            remote_jid=remote_jid, mode=mode, line_code=line_code,
        ).on_conflict_do_update(
            index_elements=["remote_jid"], set_={"mode": mode, "line_code": line_code},
        )
        with TransactionManager.get().session() as s:
            s.execute(stmt)
