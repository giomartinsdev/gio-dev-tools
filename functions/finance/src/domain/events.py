from datetime import datetime

from pydantic import BaseModel, Field


class DomainEvent(BaseModel):
    occurred_at: datetime = Field(default_factory=datetime.utcnow)


class TransactionRecorded(DomainEvent):
    transaction_id: str = ""
    amount: str = ""
    type: str = ""
    category: str = ""


class TransactionDeleted(DomainEvent):
    transaction_id: str = ""
