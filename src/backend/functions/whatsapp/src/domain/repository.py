from abc import ABC, abstractmethod
from typing import Optional

from .chat import Chat
from .message import Message, MessageStatus


class ChatRepository(ABC):
    @abstractmethod
    def save(self, chat: Chat) -> None: ...

    @abstractmethod
    def find_by_jid(self, jid: str) -> Optional[Chat]: ...

    @abstractmethod
    def find_all(self) -> list[Chat]: ...


class MessageRepository(ABC):
    @abstractmethod
    def save(self, message: Message) -> None: ...

    @abstractmethod
    def find_by_id(self, msg_id: str) -> Optional[Message]: ...

    @abstractmethod
    def find_by_chat(self, chat_jid: str, limit: int = 100) -> list[Message]: ...

    @abstractmethod
    def update_status(self, msg_id: str, status: MessageStatus) -> None: ...


class MessageGateway(ABC):
    @abstractmethod
    def send_text(self, number: str, text: str) -> dict: ...
