from __future__ import annotations

from pydantic import BaseModel

from ...domain.quote_event import QuoteEvent
from ...domain.repository import QuoteEventRepository


class GetLatestQuotesQuery(BaseModel):
    pass


class GetLatestQuotesHandler:
    def __init__(self, repo: QuoteEventRepository):
        self._repo = repo

    def handle(self, query: GetLatestQuotesQuery) -> list[QuoteEvent]:
        return self._repo.find_latest_per_ticker()
