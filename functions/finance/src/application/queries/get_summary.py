from decimal import Decimal

from pydantic import BaseModel

from ...domain.repository import TransactionRepository
from ...domain.transaction import TransactionType


class GetSummaryQuery(BaseModel):
    pass


class Summary(BaseModel):
    total_income: Decimal
    total_expenses: Decimal
    balance: Decimal
    transaction_count: int

    def to_dict(self) -> dict:
        return {
            "total_income": str(self.total_income),
            "total_expenses": str(self.total_expenses),
            "balance": str(self.balance),
            "transaction_count": self.transaction_count,
        }


class GetSummaryHandler:
    def __init__(self, repo: TransactionRepository):
        self._repo = repo

    def handle(self, _query: GetSummaryQuery) -> Summary:
        transactions = self._repo.find_all(limit=10_000)
        income = sum(
            (t.amount.amount for t in transactions if t.type == TransactionType.INCOME),
            Decimal("0"),
        )
        expenses = sum(
            (t.amount.amount for t in transactions if t.type == TransactionType.EXPENSE),
            Decimal("0"),
        )
        return Summary(
            total_income=income,
            total_expenses=expenses,
            balance=income - expenses,
            transaction_count=len(transactions),
        )
