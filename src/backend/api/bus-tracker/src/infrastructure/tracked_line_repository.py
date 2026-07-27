from typing import Optional

from shared.timezone_handler import TimezoneAware
from shared.transaction_manager import TransactionManager

from ..domain.repository import TrackedLineRepository
from ..domain.tracked_line import TrackedLine
from .models import TrackedLineModel

_SP = TimezoneAware("America/Sao_Paulo")


class PostgresTrackedLineRepository(TrackedLineRepository):
    def save(self, line: TrackedLine) -> None:
        with TransactionManager.get().session() as s:
            s.add(TrackedLineModel(
                id=line.id,
                line_code=line.line_code,
                label=line.label,
                active=line.active,
            ))

    def update(self, line: TrackedLine) -> None:
        with TransactionManager.get().session() as s:
            row = s.get(TrackedLineModel, line.id)
            if row is None or row.deleted_at is not None:
                return
            row.line_code = line.line_code
            row.label = line.label
            row.active = line.active

    def delete(self, line_id: str) -> bool:
        with TransactionManager.get().session() as s:
            row = s.get(TrackedLineModel, line_id)
            if row is None or row.deleted_at is not None:
                return False
            row.deleted_at = _SP.now
            return True

    def find_all(self) -> list[TrackedLine]:
        with TransactionManager.get().read_only() as s:
            rows = (
                s.query(TrackedLineModel)
                .filter(TrackedLineModel.deleted_at.is_(None))
                .order_by(TrackedLineModel.created_at.asc())
                .all()
            )
            return [_to_domain(r) for r in rows]

    def find_by_id(self, line_id: str) -> Optional[TrackedLine]:
        with TransactionManager.get().read_only() as s:
            row = s.get(TrackedLineModel, line_id)
            if row is None or row.deleted_at is not None:
                return None
            return _to_domain(row)


def _to_domain(row: TrackedLineModel) -> TrackedLine:
    return TrackedLine(
        id=row.id,
        line_code=row.line_code,
        label=row.label,
        active=row.active,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )
