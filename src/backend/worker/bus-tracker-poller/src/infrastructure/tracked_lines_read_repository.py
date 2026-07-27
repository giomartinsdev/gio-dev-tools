from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from shared.transaction_manager import TransactionManager


class _Base(DeclarativeBase):
    pass


class TrackedLineModel(_Base):
    """Mirrors bus-tracker api's `tracked_lines` table (see
    src/backend/api/bus-tracker/src/infrastructure/models.py) — that service
    owns the table (create_all runs there), this worker only ever reads it,
    same cross-service read pattern domain-data-insights uses against
    bzzoiro-acl/domain-persister's tables."""

    __tablename__ = "tracked_lines"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    line_code: Mapped[str] = mapped_column(String, nullable=False)
    mode: Mapped[str] = mapped_column(String, nullable=False, default="sppo")
    label: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    active: Mapped[bool] = mapped_column(nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class TrackedLinesReadRepository:
    def find_active_line_codes(self, mode: str) -> set[str]:
        """Active, non-deleted line codes for one transit mode ("sppo" or
        "brt") — SPPO and BRT have disjoint line-code spaces, so filtering
        must always be scoped to a single mode at a time."""
        with TransactionManager.get().read_only() as s:
            rows = (
                s.query(TrackedLineModel.line_code)
                .filter(
                    TrackedLineModel.active.is_(True),
                    TrackedLineModel.deleted_at.is_(None),
                    TrackedLineModel.mode == mode,
                )
                .all()
            )
            return {r[0] for r in rows}
