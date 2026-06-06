from datetime import datetime, timezone

from pydantic import BaseModel

from ...domain.chat import Chat
from ...domain.events import MessageSent
from ...domain.message import Message, MessageStatus
from ...domain.repository import ChatRepository, MessageGateway, MessageRepository
from ...infrastructure.event_bus import EventBus


class SendMessageCommand(BaseModel):
    number: str
    text: str


class SendMessageHandler:
    def __init__(
        self,
        gateway: MessageGateway,
        chat_repo: ChatRepository,
        msg_repo: MessageRepository,
        bus: EventBus,
    ):
        self._gateway = gateway
        self._chats = chat_repo
        self._msgs = msg_repo
        self._bus = bus

    def handle(self, cmd: SendMessageCommand) -> dict:
        if not cmd.number.strip():
            raise ValueError("number is required")
        if not cmd.text.strip():
            raise ValueError("message is required")

        result = self._gateway.send_text(cmd.number.strip(), cmd.text.strip())

        jid = f"{cmd.number.strip()}@s.whatsapp.net"
        key = result.get("key", {})
        msg_id = key.get("id")
        ts_raw = result.get("messageTimestamp")
        timestamp = (
            datetime.fromtimestamp(ts_raw, tz=timezone.utc)
            if isinstance(ts_raw, (int, float))
            else datetime.now(tz=timezone.utc)
        )

        chat = self._chats.find_by_jid(jid) or Chat.create(jid)
        self._chats.save(chat.on_message_sent(cmd.text.strip(), timestamp))

        if msg_id:
            self._msgs.save(Message.create(
                msg_id=msg_id,
                chat_jid=jid,
                from_me=True,
                text=cmd.text.strip(),
                timestamp=timestamp,
                status=MessageStatus.PENDING,
            ))
            self._bus.publish(MessageSent(
                message_id=msg_id,
                chat_jid=jid,
                text=cmd.text.strip(),
                number=cmd.number.strip(),
            ))

        return result
