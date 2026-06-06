from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import DateTime, Numeric, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from shared.timezone_handler import TimezoneAware

_SP = TimezoneAware("America/Sao_Paulo")


class Base(DeclarativeBase):
    pass


class TransactionModel(Base):
    __tablename__ = "transactions"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String, nullable=False, default="BRL")
    type: Mapped[str] = mapped_column(String, nullable=False)
    category: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False)
    date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: _SP.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: _SP.now, onupdate=lambda: _SP.now)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, default=None)
