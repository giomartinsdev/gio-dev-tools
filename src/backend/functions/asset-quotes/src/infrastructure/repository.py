from decimal import Decimal

from sqlalchemy import text

from shared.transaction_manager import TransactionManager

from ..domain.quote_event import QuoteEvent
from ..domain.repository import QuoteEventRepository
from .models import QuoteEventModel


class PostgresQuoteEventRepository(QuoteEventRepository):
    def save_all(self, events: list[QuoteEvent]) -> None:
        with TransactionManager.get().session() as s:
            for e in events:
                s.add(QuoteEventModel(
                    id=e.id,
                    ticker=e.ticker,
                    price=e.price,
                    daily_change=e.daily_change,
                    daily_change_pct=e.daily_change_pct,
                    last_dividend=e.last_dividend,
                    last_dividend_date=e.last_dividend_date,
                    recorded_at=e.recorded_at,
                ))

    def find_latest_per_ticker(self) -> list[QuoteEvent]:
        with TransactionManager.get().read_only() as s:
            rows = s.execute(text("""
                SELECT DISTINCT ON (ticker)
                    id, ticker, price, daily_change, daily_change_pct,
                    last_dividend, last_dividend_date, recorded_at
                FROM quote_events
                ORDER BY ticker, recorded_at DESC
            """)).fetchall()
        return [_to_domain(r) for r in rows]

    def get_asset_tickers(self) -> list[str]:
        with TransactionManager.get().read_only() as s:
            rows = s.execute(text("""
                SELECT DISTINCT ticker
                FROM assets
                WHERE ticker IS NOT NULL
                  AND ticker != ''
                  AND deleted_at IS NULL
            """)).fetchall()
        return [r.ticker for r in rows]


def _to_domain(row) -> QuoteEvent:
    return QuoteEvent(
        id=row.id,
        ticker=row.ticker,
        price=Decimal(str(row.price)) if row.price is not None else None,
        daily_change=Decimal(str(row.daily_change)) if row.daily_change is not None else None,
        daily_change_pct=Decimal(str(row.daily_change_pct)) if row.daily_change_pct is not None else None,
        last_dividend=Decimal(str(row.last_dividend)) if row.last_dividend is not None else None,
        last_dividend_date=row.last_dividend_date,
        recorded_at=row.recorded_at,
    )
