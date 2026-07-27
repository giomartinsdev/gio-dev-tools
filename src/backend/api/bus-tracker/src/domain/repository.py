from abc import ABC, abstractmethod
from typing import Optional

from .tracked_line import TrackedLine


class TrackedLineRepository(ABC):
    @abstractmethod
    def save(self, line: TrackedLine) -> None: ...

    @abstractmethod
    def update(self, line: TrackedLine) -> None: ...

    @abstractmethod
    def delete(self, line_id: str) -> bool: ...

    @abstractmethod
    def find_all(self) -> list[TrackedLine]: ...

    @abstractmethod
    def find_by_id(self, line_id: str) -> Optional[TrackedLine]: ...
