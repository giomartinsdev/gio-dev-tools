from datetime import datetime
from enum import Enum

from pydantic import BaseModel


class MessageStatus(str, Enum):
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    ERROR = "error"

    @classmethod
    def from_evolution(cls, raw: str) -> "MessageStatus":
        return {
            "ERROR": cls.ERROR,
            "PENDING": cls.PENDING,
            "SERVER_ACK": cls.SENT,
            "DELIVERY_ACK": cls.DELIVERED,
            "READ": cls.READ,
            "PLAYED": cls.READ,
        }.get(str(raw).upper(), cls.PENDING)


class Message(BaseModel):
    id: str
    chat_jid: str
    from_me: bool
    text: str
    timestamp: datetime
    status: MessageStatus = MessageStatus.PENDING

    @classmethod
    def create(
        cls,
        msg_id: str,
        chat_jid: str,
        from_me: bool,
        text: str,
        timestamp: datetime,
        status: MessageStatus = MessageStatus.PENDING,
    ) -> "Message":
        return cls(
            id=msg_id,
            chat_jid=chat_jid,
            from_me=from_me,
            text=text,
            timestamp=timestamp,
            status=status,
        )

    def with_status(self, status: MessageStatus) -> "Message":
        return self.model_copy(update={"status": status})

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "chat_jid": self.chat_jid,
            "from_me": self.from_me,
            "text": self.text,
            "timestamp": self.timestamp.isoformat(),
            "status": self.status.value,
        }
