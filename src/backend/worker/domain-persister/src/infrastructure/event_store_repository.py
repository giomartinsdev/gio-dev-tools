from __future__ import annotations

from datetime import datetime

from sqlalchemy.dialects.postgresql import insert as pg_insert

from shared.transaction_manager import TransactionManager

from .models import EventStoreModel


class EventStoreRepository:
    def append(self, event_id: str, event_type: str, occurred_at: datetime, payload: dict) -> bool:
        """Insert into the append-only event store.

        Returns True if this event_id was newly recorded, False if it was already
        present (a RabbitMQ redelivery) — the caller relies on this to stay idempotent.
        """
        stmt = pg_insert(EventStoreModel).values(
            event_id=event_id,
            event_type=event_type,
            occurred_at=occurred_at,
            payload=payload,
        ).on_conflict_do_nothing(index_elements=["event_id"])
        with TransactionManager.get().session() as s:
            result = s.execute(stmt)
            return result.rowcount > 0
