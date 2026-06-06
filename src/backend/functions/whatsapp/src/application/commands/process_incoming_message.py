from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel

from ...domain.chat import Chat
from ...domain.events import MessageReceived
from ...domain.message import Message, MessageStatus
from ...domain.repository import ChatRepository, MessageRepository
from ...infrastructure.event_bus import EventBus


def _extract_text(message: dict) -> str:
    if not message:
        return ""
    return (
        message.get("conversation")
        or (message.get("extendedTextMessage") or {}).get("text")
        or (message.get("imageMessage") or {}).get("caption")
        or (message.get("videoMessage") or {}).get("caption")
        or (message.get("documentMessage") or {}).get("title")
        or ("[Áudio]" if message.get("audioMessage") else None)
        or ("[Sticker]" if message.get("stickerMessage") else None)
        or ("[Mídia]" if any(k.endswith("Message") for k in message) else "")
        or ""
    )


def _to_ts(value) -> datetime:
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=timezone.utc)
    return datetime.now(tz=timezone.utc)


class ProcessIncomingMessageCommand(BaseModel):
    jid: str
    from_me: bool
    msg_id: str
    message_payload: dict = {}
    timestamp_unix: float = 0
    status_raw: str = "PENDING"
    push_name: Optional[str] = None


class ProcessIncomingMessageHandler:
    def __init__(self, chat_repo: ChatRepository, msg_repo: MessageRepository, bus: EventBus):
        self._chats = chat_repo
        self._msgs = msg_repo
        self._bus = bus

    def handle(self, cmd: ProcessIncomingMessageCommand) -> None:
        if not cmd.jid or cmd.jid.endswith("@g.us") or cmd.jid == "status@broadcast":
            return
        if not cmd.msg_id:
            return

        text = _extract_text(cmd.message_payload)
        timestamp = _to_ts(cmd.timestamp_unix)
        status = MessageStatus.from_evolution(cmd.status_raw)

        chat = self._chats.find_by_jid(cmd.jid) or Chat.create(cmd.jid)
        if not cmd.from_me and cmd.push_name:
            chat = chat.with_name(cmd.push_name)
        chat = chat.on_message_sent(text, timestamp) if cmd.from_me else chat.on_message_received(text, timestamp)
        self._chats.save(chat)

        self._msgs.save(Message.create(
            msg_id=cmd.msg_id,
            chat_jid=cmd.jid,
            from_me=cmd.from_me,
            text=text,
            timestamp=timestamp,
            status=status,
        ))

        if not cmd.from_me:
            self._bus.publish(MessageReceived(message_id=cmd.msg_id, chat_jid=cmd.jid, text=text))
