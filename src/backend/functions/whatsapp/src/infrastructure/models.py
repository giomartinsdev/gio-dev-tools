from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class ChatModel(Base):
    __tablename__ = "wp_chats"

    jid = Column(String, primary_key=True)
    name = Column(String, nullable=True)
    last_message_at = Column(DateTime(timezone=True), nullable=True)
    last_message_text = Column(String(500), nullable=True)
    unread_count = Column(Integer, nullable=False, default=0)
    updated_at = Column(DateTime(timezone=True), server_default=func.now())

    def to_dict(self) -> dict:
        return {
            "jid": self.jid,
            "name": self.name or self.jid.split("@")[0],
            "last_message_at": self.last_message_at.isoformat() if self.last_message_at else None,
            "last_message_text": self.last_message_text,
            "unread_count": self.unread_count,
        }


class MessageModel(Base):
    __tablename__ = "wp_messages"
    __table_args__ = (Index("ix_wp_messages_chat_ts", "chat_jid", "timestamp"),)

    id = Column(String, primary_key=True)
    chat_jid = Column(String, ForeignKey("wp_chats.jid"), nullable=False)
    from_me = Column(Boolean, nullable=False, default=False)
    text = Column(Text, nullable=False, default="")
    timestamp = Column(DateTime(timezone=True), nullable=False)
    status = Column(String(20), nullable=False, default="pending")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "chat_jid": self.chat_jid,
            "from_me": self.from_me,
            "text": self.text,
            "timestamp": self.timestamp.isoformat(),
            "status": self.status,
        }
