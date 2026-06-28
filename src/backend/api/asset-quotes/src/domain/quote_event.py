from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Optional
import uuid

from pydantic import BaseModel, ConfigDict


class QuoteEvent(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    ticker: str
    price: Optional[Decimal] = None
    daily_change: Optional[Decimal] = None
    daily_change_pct: Optional[Decimal] = None
    last_dividend: Optional[Decimal] = None
    last_dividend_date: Optional[date] = None
    recorded_at: datetime

    @classmethod
    def create(
        cls,
        ticker: str,
        price: Optional[Decimal],
        daily_change: Optional[Decimal],
        daily_change_pct: Optional[Decimal],
        last_dividend: Optional[Decimal],
        last_dividend_date: Optional[date],
        recorded_at: datetime,
    ) -> "QuoteEvent":
        return cls(
            id=str(uuid.uuid4()),
            ticker=ticker,
            price=price,
            daily_change=daily_change,
            daily_change_pct=daily_change_pct,
            last_dividend=last_dividend,
            last_dividend_date=last_dividend_date,
            recorded_at=recorded_at,
        )

    def to_dict(self) -> dict:
        return {
            "ticker": self.ticker,
            "price": str(self.price) if self.price is not None else None,
            "daily_change": str(self.daily_change) if self.daily_change is not None else None,
            "daily_change_pct": str(self.daily_change_pct) if self.daily_change_pct is not None else None,
            "last_dividend": str(self.last_dividend) if self.last_dividend is not None else None,
            "last_dividend_date": self.last_dividend_date.isoformat() if self.last_dividend_date else None,
            "recorded_at": self.recorded_at.isoformat() if self.recorded_at else None,
        }
