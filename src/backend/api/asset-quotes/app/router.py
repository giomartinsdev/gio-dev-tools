from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from src.application.commands.refresh_quotes import RefreshQuotesCommand, RefreshQuotesHandler
from src.application.queries.get_latest_quotes import GetLatestQuotesHandler, GetLatestQuotesQuery
from src.infrastructure.brapi_client import BrapiClient
from src.infrastructure.event_bus import EventBus
from src.infrastructure.repository import PostgresQuoteEventRepository

from .deps import get_bus, get_client, get_repo
from .schemas import QuoteResponse, RefreshResult

router = APIRouter()


@router.get("/quotes", response_model=list[QuoteResponse])
def get_quotes(repo: PostgresQuoteEventRepository = Depends(get_repo)):
    quotes = GetLatestQuotesHandler(repo).handle(GetLatestQuotesQuery())
    return [
        QuoteResponse(
            ticker=q.ticker,
            price=q.price,
            daily_change=q.daily_change,
            daily_change_pct=q.daily_change_pct,
            last_dividend=q.last_dividend,
            last_dividend_date=q.last_dividend_date,
            recorded_at=q.recorded_at,
        )
        for q in quotes
    ]


@router.post("/quotes/refresh", response_model=RefreshResult)
def refresh_quotes(
    repo: PostgresQuoteEventRepository = Depends(get_repo),
    bus: EventBus = Depends(get_bus),
    client: BrapiClient = Depends(get_client),
):
    try:
        result = RefreshQuotesHandler(repo, bus, client).handle(RefreshQuotesCommand())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return result.model_dump()
