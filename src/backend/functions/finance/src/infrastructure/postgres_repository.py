from decimal import Decimal
from typing import Optional

from sqlalchemy import extract, text

from shared.transaction_manager import TransactionManager
from shared.timezone_handler import TimezoneAware

from ..domain.repository import TransactionRepository
from ..domain.transaction import Money, Transaction, TransactionType
from .models import Base, TransactionModel

_SP = TimezoneAware("America/Sao_Paulo")


def migrate() -> None:
    engine = TransactionManager.get().engine
    Base.metadata.create_all(engine)
    with engine.connect() as conn:
        conn.execute(text("""
            ALTER TABLE transactions
                ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ NULL
        """))
        conn.commit()


class PostgresTransactionRepository(TransactionRepository):
    def save(self, transaction: Transaction) -> None:
        with TransactionManager.get().session() as s:
            s.add(TransactionModel(
                id=transaction.id,
                amount=transaction.amount.amount,
                currency=transaction.amount.currency,
                type=transaction.type.value,
                category=transaction.category,
                description=transaction.description,
                date=transaction.date,
            ))

    def delete(self, transaction_id: str) -> bool:
        with TransactionManager.get().session() as s:
            row = s.get(TransactionModel, transaction_id)
            if row is None or row.deleted_at is not None:
                return False
            now = _SP.now
            row.deleted_at = now
            row.updated_at = now
            return True

    def find_all(
        self,
        limit: int = 50,
        offset: int = 0,
        month: Optional[int] = None,
        year: Optional[int] = None,
    ) -> list[Transaction]:
        with TransactionManager.get().read_only() as s:
            q = s.query(TransactionModel).filter(TransactionModel.deleted_at.is_(None))
            if month is not None and year is not None:
                q = q.filter(extract("month", TransactionModel.date) == month)
                q = q.filter(extract("year", TransactionModel.date) == year)
            rows = (
                q.order_by(TransactionModel.date.desc())
                .limit(limit)
                .offset(offset)
                .all()
            )
            return [_to_domain(r) for r in rows]

    def find_by_id(self, transaction_id: str) -> Optional[Transaction]:
        with TransactionManager.get().read_only() as s:
            row = s.get(TransactionModel, transaction_id)
            if row is None or row.deleted_at is not None:
                return None
            return _to_domain(row)


def _to_domain(row: TransactionModel) -> Transaction:
    from datetime import datetime
    date = row.date if isinstance(row.date, datetime) else datetime.fromisoformat(str(row.date))
    return Transaction(
        id=row.id,
        amount=Money(amount=Decimal(str(row.amount)), currency=row.currency),
        type=TransactionType(row.type),
        category=row.category,
        description=row.description,
        date=date,
    )
