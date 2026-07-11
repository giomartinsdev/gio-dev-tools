from __future__ import annotations

from datetime import datetime

from sqlalchemy.dialects.postgresql import insert as pg_insert

from shared.transaction_manager import TransactionManager

from .models import RealtimeAlertLogModel


class RealtimeAlertLogRepository:
    def is_alerted(self, match_id: str, market: str, outcome: str) -> bool:
        with TransactionManager.get().read_only() as s:
            row = s.get(RealtimeAlertLogModel, (match_id, market, outcome))
            return row is not None

    def mark_alerted(self, match_id: str, market: str, outcome: str) -> None:
        stmt = pg_insert(RealtimeAlertLogModel).values(
            match_id=match_id, market=market, outcome=outcome, alerted_at=datetime.utcnow(),
        ).on_conflict_do_nothing(index_elements=["match_id", "market", "outcome"])
        with TransactionManager.get().session() as s:
            s.execute(stmt)
