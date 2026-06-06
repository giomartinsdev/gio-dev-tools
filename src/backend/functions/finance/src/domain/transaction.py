from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional
import uuid

from pydantic import BaseModel, ConfigDict, field_validator
from shared.timezone_handler import TimezoneAware

_SP = TimezoneAware("America/Sao_Paulo")


class TransactionType(str, Enum):
    INCOME = "income"
    EXPENSE = "expense"


class Money(BaseModel):
    model_config = ConfigDict(frozen=True)

    amount: Decimal
    currency: str = "BRL"

    @field_validator("amount")
    @classmethod
    def must_be_nonzero(cls, v: Decimal) -> Decimal:
        if v == 0:
            raise ValueError("Amount cannot be zero")
        return v

    def to_dict(self) -> dict:
        return {"amount": str(self.amount), "currency": self.currency}


class Transaction(BaseModel):
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
            date=date or _SP.now,
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
