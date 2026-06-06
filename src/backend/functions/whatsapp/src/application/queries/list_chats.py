from pydantic import BaseModel

from ...domain.repository import ChatRepository


class ListChatsQuery(BaseModel):
    pass


class ListChatsHandler:
    def __init__(self, chat_repo: ChatRepository):
        self._chats = chat_repo

    def handle(self, query: ListChatsQuery) -> list[dict]:
        return [c.to_dict() for c in self._chats.find_all()]
