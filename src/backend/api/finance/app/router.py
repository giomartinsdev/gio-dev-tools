from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from src.application.commands.record_transaction import RecordTransactionCommand, RecordTransactionHandler
from src.application.commands.update_transaction import UpdateTransactionCommand, UpdateTransactionHandler
from src.application.commands.delete_transaction import DeleteTransactionCommand, DeleteTransactionHandler
from src.application.queries.get_summary import GetSummaryQuery, GetSummaryHandler
from src.application.queries.list_transactions import ListTransactionsQuery, ListTransactionsHandler
from src.infrastructure.postgres_repository import PostgresTransactionRepository
from src.infrastructure.event_bus import EventBus

from .schemas import RecordTransactionRequest, UpdateTransactionRequest
from .deps import get_repo, get_bus

router = APIRouter()


@router.get("/transactions")
def list_transactions(
    limit: int = 50,
    offset: int = 0,
    month: Optional[int] = None,
    year: Optional[int] = None,
    repo: PostgresTransactionRepository = Depends(get_repo),
):
    transactions = ListTransactionsHandler(repo).handle(
        ListTransactionsQuery(limit=limit, offset=offset, month=month, year=year)
    )
    return [t.to_dict() for t in transactions]


@router.get("/transactions/summary")
def get_summary(
    month: Optional[int] = None,
    year: Optional[int] = None,
    repo: PostgresTransactionRepository = Depends(get_repo),
):
    return GetSummaryHandler(repo).handle(GetSummaryQuery(month=month, year=year)).to_dict()


@router.post("/transactions", status_code=201)
def record_transaction(
    body: RecordTransactionRequest,
    repo: PostgresTransactionRepository = Depends(get_repo),
    bus: EventBus = Depends(get_bus),
):
    try:
        transaction = RecordTransactionHandler(repo, bus).handle(
            RecordTransactionCommand(
                amount=body.amount,
                type=body.type,
                category=body.category,
                description=body.description,
                date=body.date,
            )
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return transaction.to_dict()


@router.patch("/transactions/{transaction_id}", status_code=200)
def update_transaction(
    transaction_id: str,
    body: UpdateTransactionRequest,
    repo: PostgresTransactionRepository = Depends(get_repo),
    bus: EventBus = Depends(get_bus),
):
    try:
        result = UpdateTransactionHandler(repo, bus).handle(
            UpdateTransactionCommand(
                transaction_id=transaction_id,
                amount=body.amount,
                type=body.type,
                category=body.category,
                description=body.description,
                date=body.date,
            )
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if result is None:
        raise HTTPException(status_code=404, detail="transaction not found")
    reversal, new_entry = result
    return {"reversal": reversal.to_dict(), "transaction": new_entry.to_dict()}


@router.delete("/transactions/{transaction_id}", status_code=200)
def delete_transaction(
    transaction_id: str,
    repo: PostgresTransactionRepository = Depends(get_repo),
    bus: EventBus = Depends(get_bus),
):
    deleted = DeleteTransactionHandler(repo, bus).handle(
        DeleteTransactionCommand(transaction_id=transaction_id)
    )
    if not deleted:
        raise HTTPException(status_code=404, detail="transaction not found")
    return {"deleted": True}
