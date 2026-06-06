from pydantic import BaseModel

from ...domain.repository import ChatRepository


class MarkChatReadCommand(BaseModel):
    jid: str


class MarkChatReadHandler:
    def __init__(self, chat_repo: ChatRepository):
        self._chats = chat_repo

    def handle(self, cmd: MarkChatReadCommand) -> None:
        chat = self._chats.find_by_jid(cmd.jid)
        if chat:
            self._chats.save(chat.on_read())
