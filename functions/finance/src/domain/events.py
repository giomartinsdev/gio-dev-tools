from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class DomainEvent:
    occurred_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class TransactionRecorded(DomainEvent):
    transaction_id: str = ""
    amount: str = ""
    type: str = ""
    category: str = ""


@dataclass
class TransactionDeleted(DomainEvent):
    transaction_id: str = ""
