from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Optional

from pydantic import BaseModel

from ...domain.repository import TransactionRepository
from ...domain.transaction import Transaction, TransactionType
from ...infrastructure.event_bus import EventBus


class UpdateTransactionCommand(BaseModel):
    transaction_id: str
    amount: str
    type: str
    category: str
    description: str
    date: Optional[str] = None


class UpdateTransactionHandler:
    def __init__(self, repo: TransactionRepository, bus: EventBus):
        self._repo = repo
        self._bus = bus

    def handle(self, cmd: UpdateTransactionCommand) -> Optional[tuple[Transaction, Transaction]]:
        original = self._repo.find_by_id(cmd.transaction_id)
        if not original:
            return None

        try:
            amount = Decimal(cmd.amount)
        except InvalidOperation:
            raise ValueError(f"Invalid amount: {cmd.amount!r}")

        try:
            t_type = TransactionType(cmd.type)
        except ValueError:
            raise ValueError(f"Invalid type {cmd.type!r}")

        if not cmd.category.strip():
            raise ValueError("category is required")
        if not cmd.description.strip():
            raise ValueError("description is required")

        new_date = datetime.fromisoformat(cmd.date) if cmd.date else original.date

        reversal = Transaction.create(
            amount=-original.amount.amount,
            type=original.type,
            category=original.category,
            description=f"[reversal] {original.description}",
            date=original.date,
        )

        new_entry = Transaction.create(
            amount=amount,
            type=t_type,
            category=cmd.category.strip(),
            description=cmd.description.strip(),
            date=new_date,
        )

        self._repo.save(reversal)
        self._repo.save(new_entry)

        return reversal, new_entry
