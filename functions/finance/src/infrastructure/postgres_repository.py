import os
from contextlib import contextmanager
from datetime import datetime
from decimal import Decimal
from typing import Optional

import psycopg2
import psycopg2.extras

from ..domain.repository import TransactionRepository
from ..domain.transaction import Money, Transaction, TransactionType

_DATABASE_URL = os.environ.get("DATABASE_URL", "")


@contextmanager
def _conn():
    conn = psycopg2.connect(_DATABASE_URL)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def migrate() -> None:
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS transactions (
                    id          TEXT PRIMARY KEY,
                    amount      NUMERIC(15, 2) NOT NULL,
                    currency    TEXT NOT NULL DEFAULT 'BRL',
                    type        TEXT NOT NULL,
                    category    TEXT NOT NULL,
                    description TEXT NOT NULL,
                    date        TIMESTAMPTZ NOT NULL
                )
            """)


class PostgresTransactionRepository(TransactionRepository):
    def save(self, transaction: Transaction) -> None:
        with _conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO transactions (id, amount, currency, type, category, description, date) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s)",
                    (
                        transaction.id,
                        transaction.amount.amount,
                        transaction.amount.currency,
                        transaction.type.value,
                        transaction.category,
                        transaction.description,
                        transaction.date,
                    ),
                )

    def delete(self, transaction_id: str) -> bool:
        with _conn() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM transactions WHERE id = %s", (transaction_id,))
                return cur.rowcount > 0

    def find_all(self, limit: int = 50, offset: int = 0) -> list[Transaction]:
        with _conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    "SELECT * FROM transactions ORDER BY date DESC LIMIT %s OFFSET %s",
                    (limit, offset),
                )
                return [_row_to_transaction(r) for r in cur.fetchall()]

    def find_by_id(self, transaction_id: str) -> Optional[Transaction]:
        with _conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("SELECT * FROM transactions WHERE id = %s", (transaction_id,))
                row = cur.fetchone()
        return _row_to_transaction(row) if row else None


def _row_to_transaction(row: dict) -> Transaction:
    date = row["date"]
    if not isinstance(date, datetime):
        date = datetime.fromisoformat(str(date))
    return Transaction(
        id=row["id"],
        amount=Money(amount=Decimal(str(row["amount"])), currency=row["currency"]),
        type=TransactionType(row["type"]),
        category=row["category"],
        description=row["description"],
        date=date,
    )
