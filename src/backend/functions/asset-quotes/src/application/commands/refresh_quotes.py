from pydantic import BaseModel

from ...domain.events import QuotesRefreshed
from ...domain.repository import QuoteEventRepository
from ...infrastructure.brapi_client import BrapiClient
from ...infrastructure.event_bus import EventBus


class RefreshQuotesCommand(BaseModel):
    pass


class RefreshQuotesResult(BaseModel):
    updated: list[str]
    failed: list[str]


class RefreshQuotesHandler:
    def __init__(self, repo: QuoteEventRepository, bus: EventBus, client: BrapiClient):
        self._repo = repo
        self._bus = bus
        self._client = client

    def handle(self, cmd: RefreshQuotesCommand) -> RefreshQuotesResult:
        tickers = self._repo.get_asset_tickers()
        if not tickers:
            return RefreshQuotesResult(updated=[], failed=[])

        events, failed = self._client.fetch_quotes(tickers)
        if events:
            self._repo.save_all(events)

        updated = [e.ticker for e in events]
        self._bus.publish(QuotesRefreshed(updated=updated, failed=failed))
        return RefreshQuotesResult(updated=updated, failed=failed)
