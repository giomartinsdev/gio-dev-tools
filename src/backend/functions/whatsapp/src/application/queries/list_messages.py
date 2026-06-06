from pydantic import BaseModel

from ...domain.repository import MessageRepository


class ListMessagesQuery(BaseModel):
    jid: str
    limit: int = 100


class ListMessagesHandler:
    def __init__(self, msg_repo: MessageRepository):
        self._msgs = msg_repo

    def handle(self, query: ListMessagesQuery) -> list[dict]:
        return [m.to_dict() for m in self._msgs.find_by_chat(query.jid, query.limit)]
