from __future__ import annotations
from abc import ABC, abstractmethod
from .command import AlexaCommand


class AlexaClientPort(ABC):
    @abstractmethod
    async def send_command(self, command: AlexaCommand) -> None: ...

    @abstractmethod
    async def get_device_names(self) -> list[str]: ...
