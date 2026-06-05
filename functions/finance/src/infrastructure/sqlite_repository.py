import os
import sqlite3
from datetime import datetime
from decimal import Decimal
from typing import Optional

from ..domain.repository import TransactionRepository
from ..domain.transaction import Money, Transaction, TransactionType

_DB_PATH = os.environ.get("FINANCE_DB_PATH", "/tmp/finance.db")


def _connect() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(_DB_PATH) or ".", exist_ok=True)
    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def migrate() -> None:
    with _connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id          TEXT PRIMARY KEY,
                amount      TEXT NOT NULL,
                currency    TEXT NOT NULL DEFAULT 'BRL',
                type        TEXT NOT NULL,
                category    TEXT NOT NULL,
                description TEXT NOT NULL,
                date        TEXT NOT NULL
            )
        """)


class SQLiteTransactionRepository(TransactionRepository):
    def save(self, transaction: Transaction) -> None:
        with _connect() as conn:
            conn.execute(
                "INSERT INTO transactions (id, amount, currency, type, category, description, date) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    transaction.id,
                    str(transaction.amount.amount),
                    transaction.amount.currency,
                    transaction.type.value,
                    transaction.category,
                    transaction.description,
                    transaction.date.isoformat(),
                ),
            )

    def delete(self, transaction_id: str) -> bool:
        with _connect() as conn:
            cursor = conn.execute(
                "DELETE FROM transactions WHERE id = ?", (transaction_id,)
            )
            return cursor.rowcount > 0

    def find_all(self, limit: int = 50, offset: int = 0) -> list[Transaction]:
        with _connect() as conn:
            rows = conn.execute(
                "SELECT * FROM transactions ORDER BY date DESC LIMIT ? OFFSET ?",
                (limit, offset),
            ).fetchall()
        return [_row_to_transaction(r) for r in rows]

    def find_by_id(self, transaction_id: str) -> Optional[Transaction]:
        with _connect() as conn:
            row = conn.execute(
                "SELECT * FROM transactions WHERE id = ?", (transaction_id,)
            ).fetchone()
        return _row_to_transaction(row) if row else None


def _row_to_transaction(row: sqlite3.Row) -> Transaction:
    return Transaction(
        id=row["id"],
        amount=Money(amount=Decimal(row["amount"]), currency=row["currency"]),
        type=TransactionType(row["type"]),
        category=row["category"],
        description=row["description"],
        date=datetime.fromisoformat(row["date"]),
    )
