from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional
import uuid

from pydantic import BaseModel, ConfigDict, field_validator


class AssetType(str, Enum):
    CDB      = "CDB"
    FII      = "FII"
    STOCK    = "Stock"
    TREASURY = "Treasury"
    SAVINGS  = "Savings"
    CRYPTO   = "Crypto"
    OTHER    = "Other"


class Asset(BaseModel):
    model_config = ConfigDict(frozen=False)

    id: str
    name: str
    type: AssetType
    institution: str
    quantity: Decimal
    purchase_price: Decimal
    currency: str = "BRL"
    ticker: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @field_validator("quantity")
    @classmethod
    def quantity_positive(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("Quantity must be positive")
        return v

    @field_validator("purchase_price")
    @classmethod
    def price_non_negative(cls, v: Decimal) -> Decimal:
        if v < 0:
            raise ValueError("Purchase price cannot be negative")
        return v

    @property
    def total_value(self) -> Decimal:
        return self.quantity * self.purchase_price

    @classmethod
    def create(
        cls,
        name: str,
        type: AssetType,
        institution: str,
        quantity: Decimal,
        purchase_price: Decimal,
        ticker: Optional[str] = None,
    ) -> "Asset":
        return cls(
            id=str(uuid.uuid4()),
            name=name,
            type=type,
            institution=institution,
            quantity=quantity,
            purchase_price=purchase_price,
            ticker=ticker or None,
        )

    def to_dict(self, quote: dict | None = None) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type.value,
            "institution": self.institution,
            "quantity": str(self.quantity),
            "purchase_price": str(self.purchase_price),
            "total_value": str(self.total_value),
            "currency": self.currency,
            "ticker": self.ticker,
            "quote": quote,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
