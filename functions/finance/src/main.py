from shared.logger import get_logger
from shared.request import Request
from shared.response import Response

from .application.commands.delete_transaction import DeleteTransactionCommand, DeleteTransactionHandler
from .application.commands.record_transaction import RecordTransactionCommand, RecordTransactionHandler
from .application.queries.get_summary import GetSummaryQuery, GetSummaryHandler
from .application.queries.list_transactions import ListTransactionsQuery, ListTransactionsHandler
from .domain.events import TransactionDeleted, TransactionRecorded
from .infrastructure.event_bus import get_event_bus
from .infrastructure.postgres_repository import PostgresTransactionRepository, migrate

logger = get_logger(__name__)

migrate()

_repo = PostgresTransactionRepository()
_bus = get_event_bus()
_bus.subscribe(TransactionRecorded, lambda e: logger.info(f"TransactionRecorded id={e.transaction_id} type={e.type} amount={e.amount}"))
_bus.subscribe(TransactionDeleted, lambda e: logger.info(f"TransactionDeleted id={e.transaction_id}"))


def main(request: Request) -> Response:
    try:
        if request.method == "POST":
            return _record(request)
        if request.method == "DELETE":
            return _delete(request)
        if request.method == "GET":
            return _summary(request) if request.query.get("summary") == "true" else _list(request)
        return Response(
            body={"error": "method not allowed"},
            status_code=405
        )

    except ValueError as e:
        return Response(
            body={"error": str(e)},
            status_code=400
        )
    except Exception as e:
        logger.error(
            f"unhandled error: {e}",
            exc_info=True
        )
        return Response(
            body={"error": "internal server error"},
            status_code=500
        )


def _record(request: Request) -> Response:
    cmd = RecordTransactionCommand(
        amount=str(request.body.get("amount", "")),
        type=str(request.body.get("type", "")),
        category=str(request.body.get("category", "")),
        description=str(request.body.get("description", "")),
        date=request.body.get("date"),
    )
    return Response(
        body=RecordTransactionHandler(_repo, _bus).handle(cmd).to_dict(),
        status_code=201
    )


def _delete(request: Request) -> Response:
    deleted = DeleteTransactionHandler(_repo, _bus).handle(
        DeleteTransactionCommand(transaction_id=str(request.body.get("id")))
    )
    if not deleted:
        return Response(
            body={"error": "transaction not found"},
            status_code=404
        )

    return Response(
        body={"deleted": True},
        status_code=200
    )


def _list(request: Request) -> Response:
    month = int(request.query["month"]) if request.query.get("month") else None
    year = int(request.query["year"]) if request.query.get("year") else None
    return Response(
        body=[
            t.to_dict() for t in ListTransactionsHandler(_repo).handle(
                ListTransactionsQuery(
                    limit=int(request.query.get("limit", 50)),
                    offset=int(request.query.get("offset", 0)),
                    month=month,
                    year=year,
                )
            )
        ],
        status_code=200
    )


def _summary(request: Request) -> Response:
    month = int(request.query["month"]) if request.query.get("month") else None
    year = int(request.query["year"]) if request.query.get("year") else None
    return Response(
        body=GetSummaryHandler(_repo).handle(GetSummaryQuery(month=month, year=year)).to_dict(),
        status_code=200
    )
