from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import Date, DateTime, Index, Numeric, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from shared.timezone_handler import TimezoneAware

_SP = TimezoneAware("America/Sao_Paulo")


class Base(DeclarativeBase):
    pass


class QuoteEventModel(Base):
    __tablename__ = "quote_events"
    __table_args__ = (
        Index("idx_quote_events_ticker_recorded", "ticker", "recorded_at"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    ticker: Mapped[str] = mapped_column(String, nullable=False)
    price: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 4), nullable=True)
    daily_change: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 4), nullable=True)
    daily_change_pct: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 4), nullable=True)
    last_dividend: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 6), nullable=True)
    last_dividend_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
