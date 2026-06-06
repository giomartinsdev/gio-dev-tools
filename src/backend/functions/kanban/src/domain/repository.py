from abc import ABC, abstractmethod
from typing import Optional

from .board import Board
from .card import Card


class BoardRepository(ABC):
    @abstractmethod
    def save(self, board: Board) -> None: ...

    @abstractmethod
    def find_all(self) -> list[Board]: ...

    @abstractmethod
    def find_by_id(self, board_id: str) -> Optional[Board]: ...

    @abstractmethod
    def delete(self, board_id: str) -> bool: ...


class CardRepository(ABC):
    @abstractmethod
    def save(self, card: Card) -> None: ...

    @abstractmethod
    def find_by_board(self, board_id: str) -> list[Card]: ...

    @abstractmethod
    def find_by_id(self, card_id: str) -> Optional[Card]: ...

    @abstractmethod
    def delete(self, card_id: str) -> bool: ...
