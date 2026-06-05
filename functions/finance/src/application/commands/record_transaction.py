from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Optional

from pydantic import BaseModel

from ...domain.events import TransactionRecorded
from ...domain.repository import TransactionRepository
from ...domain.transaction import Transaction, TransactionType
from ...infrastructure.event_bus import EventBus


class RecordTransactionCommand(BaseModel):
    amount: str
    type: str
    category: str
    description: str
    date: Optional[str] = None


class RecordTransactionHandler:
    def __init__(self, repo: TransactionRepository, bus: EventBus):
        self._repo = repo
        self._bus = bus

    def handle(self, cmd: RecordTransactionCommand) -> Transaction:
        try:
            amount = Decimal(cmd.amount)
        except InvalidOperation:
            raise ValueError(f"Invalid amount: {cmd.amount!r}")

        try:
            t_type = TransactionType(cmd.type)
        except ValueError:
            raise ValueError(f"Invalid type {cmd.type!r}. Must be 'income' or 'expense'")

        if not cmd.category.strip():
            raise ValueError("category is required")
        if not cmd.description.strip():
            raise ValueError("description is required")

        date = datetime.fromisoformat(cmd.date) if cmd.date else None

        transaction = Transaction.create(
            amount=amount,
            type=t_type,
            category=cmd.category.strip(),
            description=cmd.description.strip(),
            date=date,
        )

        self._repo.save(transaction)

        self._bus.publish(
            TransactionRecorded(
                transaction_id=transaction.id,
                amount=str(transaction.amount.amount),
                type=transaction.type.value,
                category=transaction.category,
            )
        )

        return transaction
