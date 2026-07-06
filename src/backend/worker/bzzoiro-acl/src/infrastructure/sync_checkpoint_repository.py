from __future__ import annotations

from typing import Optional

from sqlalchemy.dialects.postgresql import insert as pg_insert

from shared.transaction_manager import TransactionManager

from .models import SyncCheckpointModel


class SyncCheckpointRepository:
    """Tracks per-feed_type sync progress, owned by bzzoiro-acl alone.

    `cursor` is an opaque string each poll handler defines the meaning of
    (e.g. an ISO timestamp for odds' `updated_after`, or a "last full sync"
    timestamp for teams). Nothing outside bzzoiro-acl reads or writes this.
    """

    def get_cursor(self, feed_type: str) -> Optional[str]:
        with TransactionManager.get().read_only() as s:
            row = s.get(SyncCheckpointModel, feed_type)
            return row.cursor if row else None

    def set_cursor(self, feed_type: str, cursor: str) -> None:
        stmt = pg_insert(SyncCheckpointModel).values(feed_type=feed_type, cursor=cursor)
        stmt = stmt.on_conflict_do_update(
            index_elements=["feed_type"],
            set_={"cursor": stmt.excluded.cursor},
        )
        with TransactionManager.get().session() as s:
            s.execute(stmt)

    def clear(self, feed_type: str) -> None:
        with TransactionManager.get().session() as s:
            row = s.get(SyncCheckpointModel, feed_type)
            if row is not None:
                s.delete(row)

    def clear_all(self) -> None:
        with TransactionManager.get().session() as s:
            s.query(SyncCheckpointModel).delete()
