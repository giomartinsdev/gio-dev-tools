import os
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

import httpx
from shared.logger import get_logger
from shared.request import Request
from shared.response import Response
from shared.transaction_manager import TransactionConfig, TransactionManager
from sqlalchemy import text

logger = get_logger(__name__)

_BRAPI_BASE = "https://brapi.dev/api"
_BRAPI_TOKEN = os.environ.get("BRAPI_TOKEN", "")

TransactionManager.configure(TransactionConfig(url=os.environ["DATABASE_URL"]))

_engine = TransactionManager.get().engine
with _engine.begin() as _conn:
    _conn.execute(text("""
        CREATE TABLE IF NOT EXISTS quote_events (
            id                  VARCHAR PRIMARY KEY,
            ticker              VARCHAR NOT NULL,
            price               NUMERIC(15, 4),
            daily_change        NUMERIC(15, 4),
            daily_change_pct    NUMERIC(8, 4),
            last_dividend       NUMERIC(15, 6),
            last_dividend_date  DATE,
            recorded_at         TIMESTAMP WITH TIME ZONE NOT NULL
        )
    """))
    _conn.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_quote_events_ticker_recorded
        ON quote_events (ticker, recorded_at DESC)
    """))


def _get_tickers() -> list[str]:
    with _engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT DISTINCT ticker
            FROM assets
            WHERE ticker IS NOT NULL
              AND ticker != ''
              AND deleted_at IS NULL
        """)).fetchall()
    return [r.ticker for r in rows]


def _fetch_brapi(tickers: list[str]) -> dict:
    params = {"dividends": "true"}
    if _BRAPI_TOKEN:
        params["token"] = _BRAPI_TOKEN
    tickers_csv = ",".join(tickers)
    with httpx.Client(timeout=15.0) as client:
        resp = client.get(f"{_BRAPI_BASE}/quote/{tickers_csv}", params=params)
        resp.raise_for_status()
    return resp.json()


def _parse_last_dividend(results_item: dict) -> tuple[Decimal | None, date | None]:
    dividends = results_item.get("dividendsData") or {}
    cash = dividends.get("cashDividends") or []
    if not cash:
        return None, None
    latest = cash[0]
    value = Decimal(str(latest["rate"])) if latest.get("rate") is not None else None
    pay_date = None
    raw_date = latest.get("paymentDate") or latest.get("lastDatePrior")
    if raw_date:
        try:
            pay_date = date.fromisoformat(raw_date[:10])
        except ValueError:
            pass
    return value, pay_date


def _update_quotes() -> dict:
    tickers = _get_tickers()
    if not tickers:
        return {"updated": [], "failed": [], "message": "no tickers found"}

    try:
        data = _fetch_brapi(tickers)
    except Exception as e:
        logger.error(f"brapi fetch failed: {e}")
        return {"updated": [], "failed": tickers, "error": str(e)}

    results = data.get("results") or []
    now = datetime.now(tz=timezone.utc)
    updated = []
    failed = []

    with _engine.begin() as conn:
        for item in results:
            ticker = item.get("symbol")
            if not ticker:
                continue
            try:
                price = Decimal(str(item["regularMarketPrice"])) if item.get("regularMarketPrice") is not None else None
                daily_change = Decimal(str(item["regularMarketChange"])) if item.get("regularMarketChange") is not None else None
                daily_change_pct = Decimal(str(item["regularMarketChangePercent"])) if item.get("regularMarketChangePercent") is not None else None
                last_dividend, last_dividend_date = _parse_last_dividend(item)

                conn.execute(text("""
                    INSERT INTO quote_events
                        (id, ticker, price, daily_change, daily_change_pct,
                         last_dividend, last_dividend_date, recorded_at)
                    VALUES
                        (:id, :ticker, :price, :daily_change, :daily_change_pct,
                         :last_dividend, :last_dividend_date, :recorded_at)
                """), {
                    "id": str(uuid.uuid4()),
                    "ticker": ticker,
                    "price": price,
                    "daily_change": daily_change,
                    "daily_change_pct": daily_change_pct,
                    "last_dividend": last_dividend,
                    "last_dividend_date": last_dividend_date,
                    "recorded_at": now,
                })
                updated.append(ticker)
                logger.info(f"quote recorded: {ticker} price={price} change={daily_change_pct}%")
            except Exception as e:
                logger.error(f"failed to record quote for {ticker}: {e}")
                failed.append(ticker)

    missing = set(tickers) - {r.get("symbol") for r in results}
    failed.extend(missing)

    return {"updated": updated, "failed": failed}


def _latest_quotes() -> list[dict]:
    with _engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT DISTINCT ON (ticker)
                ticker, price, daily_change, daily_change_pct,
                last_dividend, last_dividend_date, recorded_at
            FROM quote_events
            ORDER BY ticker, recorded_at DESC
        """)).fetchall()
    return [dict(r._mapping) for r in rows]


def main(request: Request) -> Response:
    try:
        if request.method == "POST":
            result = _update_quotes()
            return Response(body=result, status_code=200)

        if request.method == "GET":
            quotes = _latest_quotes()
            return Response(body=[
                {
                    **q,
                    "price": str(q["price"]) if q.get("price") is not None else None,
                    "daily_change": str(q["daily_change"]) if q.get("daily_change") is not None else None,
                    "daily_change_pct": str(q["daily_change_pct"]) if q.get("daily_change_pct") is not None else None,
                    "last_dividend": str(q["last_dividend"]) if q.get("last_dividend") is not None else None,
                    "last_dividend_date": q["last_dividend_date"].isoformat() if q.get("last_dividend_date") else None,
                    "recorded_at": q["recorded_at"].isoformat() if q.get("recorded_at") else None,
                }
                for q in quotes
            ], status_code=200)

        return Response(body={"error": "method not allowed"}, status_code=405)

    except Exception as e:
        logger.error(f"unhandled error: {e}", exc_info=True)
        return Response(body={"error": "internal server error"}, status_code=500)
