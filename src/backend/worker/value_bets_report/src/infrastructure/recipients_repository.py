from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from shared.transaction_manager import TransactionManager

from .models import RecipientModel


@dataclass
class Recipient:
    id: int
    phone_number: str
    name: Optional[str]
    active: bool
    realtime_alerts: bool = False


def _to_dataclass(row: RecipientModel) -> Recipient:
    return Recipient(
        id=row.id, phone_number=row.phone_number, name=row.name,
        active=row.active, realtime_alerts=row.realtime_alerts,
    )


class RecipientsRepository:
    def list_all(self) -> list[Recipient]:
        with TransactionManager.get().read_only() as s:
            rows = s.query(RecipientModel).order_by(RecipientModel.created_at.asc()).all()
            return [_to_dataclass(r) for r in rows]

    def list_active(self) -> list[Recipient]:
        with TransactionManager.get().read_only() as s:
            rows = s.query(RecipientModel).filter(RecipientModel.active.is_(True)).all()
            return [_to_dataclass(r) for r in rows]

    def list_realtime_subscribers(self) -> list[Recipient]:
        with TransactionManager.get().read_only() as s:
            rows = s.query(RecipientModel).filter(
                RecipientModel.active.is_(True), RecipientModel.realtime_alerts.is_(True),
            ).all()
            return [_to_dataclass(r) for r in rows]

    def create(self, phone_number: str, name: Optional[str], realtime_alerts: bool = False) -> Recipient:
        with TransactionManager.get().session() as s:
            row = RecipientModel(phone_number=phone_number, name=name, realtime_alerts=realtime_alerts)
            s.add(row)
            s.flush()
            s.refresh(row)
            return _to_dataclass(row)

    def delete(self, recipient_id: int) -> None:
        with TransactionManager.get().session() as s:
            s.query(RecipientModel).filter(RecipientModel.id == recipient_id).delete()

    def set_active(self, recipient_id: int, active: bool) -> Optional[Recipient]:
        with TransactionManager.get().session() as s:
            row = s.get(RecipientModel, recipient_id)
            if row is None:
                return None
            row.active = active
            s.flush()
            s.refresh(row)
            return _to_dataclass(row)

    def set_realtime_alerts(self, recipient_id: int, realtime_alerts: bool) -> Optional[Recipient]:
        with TransactionManager.get().session() as s:
            row = s.get(RecipientModel, recipient_id)
            if row is None:
                return None
            row.realtime_alerts = realtime_alerts
            s.flush()
            s.refresh(row)
            return _to_dataclass(row)
