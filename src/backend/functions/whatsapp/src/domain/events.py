from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class DomainEvent(BaseModel):
    occurred_at: datetime = Field(default_factory=datetime.utcnow)


class MessageReceived(DomainEvent):
    message_id: str = ""
    chat_jid: str = ""
    text: str = ""


class MessageSent(DomainEvent):
    message_id: str = ""
    chat_jid: str = ""
    text: str = ""
    number: str = ""


class MessageStatusUpdated(DomainEvent):
    message_id: str = ""
    status: str = ""


class ChatUpdated(DomainEvent):
    jid: str = ""
    name: Optional[str] = None
