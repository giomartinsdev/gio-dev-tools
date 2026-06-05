from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional
import uuid


class TransactionType(str, Enum):
    INCOME = "income"
    EXPENSE = "expense"


@dataclass(frozen=True)
class Money:
    amount: Decimal
    currency: str = "BRL"

    def __post_init__(self):
        if self.amount <= 0:
            raise ValueError("Amount must be positive")

    def to_dict(self) -> dict:
        return {"amount": str(self.amount), "currency": self.currency}


@dataclass
class Transaction:
    id: str
    amount: Money
    type: TransactionType
    category: str
    description: str
    date: datetime

    @classmethod
    def create(
        cls,
        amount: Decimal,
        type: TransactionType,
        category: str,
        description: str,
        date: Optional[datetime] = None,
    ) -> "Transaction":
        return cls(
            id=str(uuid.uuid4()),
            amount=Money(amount=amount),
            type=type,
            category=category,
            description=description,
            date=date or datetime.utcnow(),
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "amount": self.amount.to_dict(),
            "type": self.type.value,
            "category": self.category,
            "description": self.description,
            "date": self.date.isoformat(),
        }
