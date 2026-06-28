from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

import httpx
from shared.logger import get_logger

from ..domain.quote_event import QuoteEvent

logger = get_logger(__name__)

_BRAPI_BASE = "https://brapi.dev/api"


class BrapiClient:
    def __init__(self, token: str = ""):
        self._token = token

    def fetch_quotes(self, tickers: list[str]) -> tuple[list[QuoteEvent], list[str]]:
        headers: dict = {"Authorization": f"Bearer {self._token}"}
        now = datetime.now(tz=timezone.utc)
        events: list[QuoteEvent] = []
        failed: list[str] = []

        with httpx.Client(timeout=15.0) as client:
            for ticker in tickers:
                try:
                    resp = client.get(
                        f"{_BRAPI_BASE}/quote/{ticker}",
                        headers=headers,
                    )
                    resp.raise_for_status()
                    results = resp.json().get("results") or []
                    if not results:
                        logger.warning(f"no results for {ticker}")
                        failed.append(ticker)
                        continue
                    item = results[0]
                    events.append(QuoteEvent.create(
                        ticker=ticker,
                        price=_decimal(item.get("regularMarketPrice")),
                        daily_change=_decimal(item.get("regularMarketChange")),
                        daily_change_pct=_decimal(item.get("regularMarketChangePercent")),
                        last_dividend=None,
                        last_dividend_date=None,
                        recorded_at=now,
                    ))
                    logger.info(f"fetched quote: {ticker} price={item.get('regularMarketPrice')}")
                except Exception as e:
                    logger.error(f"failed to fetch quote for {ticker}: {e}")
                    failed.append(ticker)

        return events, failed


def _decimal(val) -> Optional[Decimal]:
    return Decimal(str(val)) if val is not None else None
