from __future__ import annotations

from abc import ABC, abstractmethod

from .conversation_state import ConversationState


class ConversationStateRepository(ABC):
    @abstractmethod
    def get(self, remote_jid: str) -> ConversationState: ...

    @abstractmethod
    def set_location(self, remote_jid: str, lat: float, lon: float) -> None: ...

    @abstractmethod
    def set_line(self, remote_jid: str, mode: str, line_code: str) -> None: ...
