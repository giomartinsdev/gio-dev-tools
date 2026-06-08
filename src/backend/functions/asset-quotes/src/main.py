import os

from shared.logger import get_logger
from shared.request import Request
from shared.response import Response
from shared.transaction_manager import TransactionConfig, TransactionManager

from .application.commands.refresh_quotes import RefreshQuotesCommand, RefreshQuotesHandler
from .application.queries.get_latest_quotes import GetLatestQuotesHandler, GetLatestQuotesQuery
from .domain.events import QuotesRefreshed
from .infrastructure.brapi_client import BrapiClient
from .infrastructure.event_bus import get_event_bus
from .infrastructure.models import Base
from .infrastructure.repository import PostgresQuoteEventRepository

logger = get_logger(__name__)

TransactionManager.configure(TransactionConfig(url=os.environ["DATABASE_URL"]))
Base.metadata.create_all(TransactionManager.get().engine)

_repo = PostgresQuoteEventRepository()
_bus = get_event_bus()
_client = BrapiClient(token=os.environ.get("BRAPI_TOKEN", ""))

_bus.subscribe(
    QuotesRefreshed,
    lambda e: logger.info(f"QuotesRefreshed updated={e.updated} failed={e.failed}"),
)


def main(request: Request) -> Response:
    try:
        if request.method == "POST":
            result = RefreshQuotesHandler(_repo, _bus, _client).handle(RefreshQuotesCommand())
            return Response(body=result.model_dump(), status_code=200)

        if request.method == "GET":
            quotes = GetLatestQuotesHandler(_repo).handle(GetLatestQuotesQuery())
            return Response(body=[q.to_dict() for q in quotes], status_code=200)

        return Response(body={"error": "method not allowed"}, status_code=405)

    except Exception as e:
        logger.error(f"unhandled error: {e}", exc_info=True)
        return Response(body={"error": "internal server error"}, status_code=500)
