from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel


class QuoteResponse(BaseModel):
    ticker: str
    price: Optional[Decimal] = None
    daily_change: Optional[Decimal] = None
    daily_change_pct: Optional[Decimal] = None
    last_dividend: Optional[Decimal] = None
    last_dividend_date: Optional[date] = None
    recorded_at: Optional[datetime] = None


class RefreshResult(BaseModel):
    updated: list[str]
    failed: list[str]
