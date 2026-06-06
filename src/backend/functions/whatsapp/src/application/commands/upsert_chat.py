from typing import Optional

from pydantic import BaseModel

from ...domain.chat import Chat
from ...domain.events import ChatUpdated
from ...domain.repository import ChatRepository
from ...infrastructure.event_bus import EventBus


class UpsertChatCommand(BaseModel):
    jid: str
    name: Optional[str] = None


class UpsertChatHandler:
    def __init__(self, chat_repo: ChatRepository, bus: EventBus):
        self._chats = chat_repo
        self._bus = bus

    def handle(self, cmd: UpsertChatCommand) -> None:
        if not cmd.jid or cmd.jid.endswith("@g.us"):
            return
        chat = self._chats.find_by_jid(cmd.jid) or Chat.create(cmd.jid)
        if cmd.name:
            chat = chat.with_name(cmd.name)
        self._chats.save(chat)
        self._bus.publish(ChatUpdated(jid=cmd.jid, name=cmd.name))
