from abc import ABC, abstractmethod
from typing import Optional
from .transaction import Transaction


class TransactionRepository(ABC):
    @abstractmethod
    def save(self, transaction: Transaction) -> None: ...

    @abstractmethod
    def delete(self, transaction_id: str) -> bool: ...

    @abstractmethod
    def find_all(self, limit: int = 50, offset: int = 0) -> list[Transaction]: ...

    @abstractmethod
    def find_by_id(self, transaction_id: str) -> Optional[Transaction]: ...
