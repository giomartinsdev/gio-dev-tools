from pydantic import BaseModel

from ...domain.repository import TransactionRepository
from ...domain.transaction import Transaction


class ListTransactionsQuery(BaseModel):
    limit: int = 50
    offset: int = 0


class ListTransactionsHandler:
    def __init__(self, repo: TransactionRepository):
        self._repo = repo

    def handle(self, query: ListTransactionsQuery) -> list[Transaction]:
        return self._repo.find_all(limit=query.limit, offset=query.offset)