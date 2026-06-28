from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class DomainEvent:
    occurred_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class BoardCreated(DomainEvent):
    board_id: str = ""
    name: str = ""


@dataclass
class BoardDeleted(DomainEvent):
    board_id: str = ""


@dataclass
class CardCreated(DomainEvent):
    card_id: str = ""
    board_id: str = ""
    title: str = ""
    status: str = ""


@dataclass
class CardUpdated(DomainEvent):
    card_id: str = ""
    board_id: str = ""
    title: str = ""
    status: str = ""


@dataclass
class CardDeleted(DomainEvent):
    card_id: str = ""
