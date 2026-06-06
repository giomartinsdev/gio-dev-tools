from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class Chat(BaseModel):
    jid: str
    name: Optional[str] = None
    last_message_at: Optional[datetime] = None
    last_message_text: Optional[str] = None
    unread_count: int = 0

    @classmethod
    def create(cls, jid: str, name: Optional[str] = None) -> "Chat":
        return cls(jid=jid, name=name)

    def on_message_received(self, text: str, timestamp: datetime) -> "Chat":
        return self.model_copy(update={
            "last_message_text": text or None,
            "last_message_at": timestamp,
            "unread_count": self.unread_count + 1,
        })

    def on_message_sent(self, text: str, timestamp: datetime) -> "Chat":
        return self.model_copy(update={
            "last_message_text": text or None,
            "last_message_at": timestamp,
        })

    def on_read(self) -> "Chat":
        return self.model_copy(update={"unread_count": 0})

    def with_name(self, name: str) -> "Chat":
        return self.model_copy(update={"name": name})

    def to_dict(self) -> dict:
        return {
            "jid": self.jid,
            "name": self.name,
            "last_message_at": self.last_message_at.isoformat() if self.last_message_at else None,
            "last_message_text": self.last_message_text,
            "unread_count": self.unread_count,
        }
