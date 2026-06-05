import os
from contextlib import contextmanager
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from ..domain.repository import TransactionRepository
from ..domain.transaction import Money, Transaction, TransactionType
from .models import Base, TransactionModel

_engine = create_engine(os.environ["DATABASE_URL"])


@contextmanager
def _session():
    with Session(_engine) as session, session.begin():
        yield session


def migrate() -> None:
    Base.metadata.create_all(_engine)


class PostgresTransactionRepository(TransactionRepository):
    def save(self, transaction: Transaction) -> None:
        with _session() as s:
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
        with _session() as s:
            row = s.get(TransactionModel, transaction_id)
            if row is None:
                return False
            s.delete(row)
            return True

    def find_all(self, limit: int = 50, offset: int = 0) -> list[Transaction]:
        with _session() as s:
            rows = (
                s.query(TransactionModel)
                .order_by(TransactionModel.date.desc())
                .limit(limit)
                .offset(offset)
                .all()
            )
            return [_to_domain(r) for r in rows]

    def find_by_id(self, transaction_id: str) -> Optional[Transaction]:
        with _session() as s:
            row = s.get(TransactionModel, transaction_id)
            return _to_domain(row) if row else None


def _to_domain(row: TransactionModel) -> Transaction:
    date = row.date if isinstance(row.date, datetime) else datetime.fromisoformat(str(row.date))
    return Transaction(
        id=row.id,
        amount=Money(amount=Decimal(str(row.amount)), currency=row.currency),
        type=TransactionType(row.type),
        category=row.category,
        description=row.description,
        date=date,
    )
