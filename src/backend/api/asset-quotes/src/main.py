from __future__ import annotations

import threading

from shared.logger import get_logger
from shared.request import Request
from shared.response import Response
from shared.secret_manager import SecretManager
from shared.transaction_manager import TransactionConfig, TransactionManager

from .application.commands.refresh_quotes import RefreshQuotesCommand, RefreshQuotesHandler
from .application.queries.get_latest_quotes import GetLatestQuotesHandler, GetLatestQuotesQuery
from .domain.events import QuotesRefreshed
from .infrastructure.brapi_client import BrapiClient
from .infrastructure.event_bus import get_event_bus
from .infrastructure.models import Base
from .infrastructure.repository import PostgresQuoteEventRepository

logger = get_logger(__name__)

_repo = None
_bus = None
_client = None
_init_done = threading.Event()
_init_error: Exception | None = None


def _init():
    global _repo, _bus, _client, _init_error
    if _repo is not None:
        _init_done.set()
        return
    try:
        sm = SecretManager()
        TransactionManager.configure(TransactionConfig(url=sm.get_secret("DATABASE_URL")))
        Base.metadata.create_all(TransactionManager.get().engine)
        _repo = PostgresQuoteEventRepository()
        _bus = get_event_bus()
        _client = BrapiClient(token=sm.get_secret("BRAPI_TOKEN"))
        _bus.subscribe(
            QuotesRefreshed,
            lambda e: logger.info(f"QuotesRefreshed updated={e.updated} failed={e.failed}"),
        )
    except Exception as e:
        _init_error = e
        logger.error(f"init failed: {e}", exc_info=True)
    finally:
        _init_done.set()


threading.Thread(target=_init, daemon=True).start()


def main(request: Request) -> Response:
    _init_done.wait()
    if _init_error is not None:
        return Response(body={"error": "service unavailable"}, status_code=503)
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
