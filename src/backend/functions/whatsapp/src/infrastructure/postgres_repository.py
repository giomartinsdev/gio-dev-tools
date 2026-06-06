from datetime import datetime, timezone
from typing import Optional

from shared.transaction_manager import TransactionManager

from ..domain.chat import Chat
from ..domain.message import Message, MessageStatus
from ..domain.repository import ChatRepository, MessageRepository
from .models import ChatModel, MessageModel


class PostgresChatRepository(ChatRepository):
    def save(self, chat: Chat) -> None:
        with TransactionManager.get().session() as s:
            row = s.query(ChatModel).filter(ChatModel.jid == chat.jid).first()
            if row:
                row.name = chat.name
                row.last_message_at = chat.last_message_at
                row.last_message_text = chat.last_message_text
                row.unread_count = chat.unread_count
            else:
                s.add(ChatModel(
                    jid=chat.jid,
                    name=chat.name,
                    last_message_at=chat.last_message_at,
                    last_message_text=chat.last_message_text,
                    unread_count=chat.unread_count,
                ))

    def find_by_jid(self, jid: str) -> Optional[Chat]:
        with TransactionManager.get().read_only() as s:
            row = s.query(ChatModel).filter(ChatModel.jid == jid).first()
            return _chat_to_domain(row) if row else None

    def find_all(self) -> list[Chat]:
        with TransactionManager.get().read_only() as s:
            rows = (
                s.query(ChatModel)
                .order_by(ChatModel.last_message_at.desc().nulls_last())
                .all()
            )
            return [_chat_to_domain(r) for r in rows]


class PostgresMessageRepository(MessageRepository):
    def save(self, message: Message) -> None:
        with TransactionManager.get().session() as s:
            row = s.query(MessageModel).filter(MessageModel.id == message.id).first()
            if row:
                if message.status != MessageStatus.PENDING:
                    row.status = message.status.value
            else:
                s.add(MessageModel(
                    id=message.id,
                    chat_jid=message.chat_jid,
                    from_me=message.from_me,
                    text=message.text,
                    timestamp=message.timestamp,
                    status=message.status.value,
                ))

    def find_by_id(self, msg_id: str) -> Optional[Message]:
        with TransactionManager.get().read_only() as s:
            row = s.query(MessageModel).filter(MessageModel.id == msg_id).first()
            return _msg_to_domain(row) if row else None

    def find_by_chat(self, chat_jid: str, limit: int = 100) -> list[Message]:
        with TransactionManager.get().read_only() as s:
            rows = (
                s.query(MessageModel)
                .filter(MessageModel.chat_jid == chat_jid)
                .order_by(MessageModel.timestamp.asc())
                .limit(limit)
                .all()
            )
            return [_msg_to_domain(r) for r in rows]

    def update_status(self, msg_id: str, status: MessageStatus) -> None:
        with TransactionManager.get().session() as s:
            row = s.query(MessageModel).filter(MessageModel.id == msg_id).first()
            if row:
                row.status = status.value


def _chat_to_domain(row: ChatModel) -> Chat:
    return Chat(
        jid=row.jid,
        name=row.name,
        last_message_at=_ensure_tz(row.last_message_at),
        last_message_text=row.last_message_text,
        unread_count=row.unread_count or 0,
    )


def _msg_to_domain(row: MessageModel) -> Message:
    return Message(
        id=row.id,
        chat_jid=row.chat_jid,
        from_me=row.from_me,
        text=row.text,
        timestamp=_ensure_tz(row.timestamp),
        status=MessageStatus(row.status),
    )


def _ensure_tz(dt) -> Optional[datetime]:
    if dt is None:
        return None
    if isinstance(dt, datetime) and dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt
