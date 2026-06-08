from datetime import date, datetime, timezone
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
        params: dict = {"dividends": "true"}
        if self._token:
            params["token"] = self._token

        try:
            with httpx.Client(timeout=15.0) as client:
                resp = client.get(f"{_BRAPI_BASE}/quote/{','.join(tickers)}", params=params)
                resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            logger.error(f"brapi request failed: {e}")
            return [], list(tickers)

        results = data.get("results") or []
        returned = {r.get("symbol") for r in results}
        failed = [t for t in tickers if t not in returned]

        now = datetime.now(tz=timezone.utc)
        events: list[QuoteEvent] = []

        for item in results:
            ticker = item.get("symbol")
            if not ticker:
                continue
            try:
                events.append(QuoteEvent.create(
                    ticker=ticker,
                    price=_decimal(item.get("regularMarketPrice")),
                    daily_change=_decimal(item.get("regularMarketChange")),
                    daily_change_pct=_decimal(item.get("regularMarketChangePercent")),
                    last_dividend=_parse_dividend_value(item),
                    last_dividend_date=_parse_dividend_date(item),
                    recorded_at=now,
                ))
            except Exception as e:
                logger.error(f"failed to parse quote for {ticker}: {e}")
                failed.append(ticker)

        return events, failed


def _decimal(val) -> Optional[Decimal]:
    return Decimal(str(val)) if val is not None else None


def _parse_dividend_value(item: dict) -> Optional[Decimal]:
    cash = (item.get("dividendsData") or {}).get("cashDividends") or []
    if not cash:
        return None
    rate = cash[0].get("rate")
    return Decimal(str(rate)) if rate is not None else None


def _parse_dividend_date(item: dict) -> Optional[date]:
    cash = (item.get("dividendsData") or {}).get("cashDividends") or []
    if not cash:
        return None
    raw = cash[0].get("paymentDate") or cash[0].get("lastDatePrior")
    if not raw:
        return None
    try:
        return date.fromisoformat(raw[:10])
    except ValueError:
        return None
