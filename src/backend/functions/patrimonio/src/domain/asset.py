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
    amount: Decimal
    currency: str = "BRL"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @field_validator("amount")
    @classmethod
    def must_be_non_negative(cls, v: Decimal) -> Decimal:
        if v < 0:
            raise ValueError("Amount cannot be negative")
        return v

    @classmethod
    def create(cls, name: str, type: AssetType, institution: str, amount: Decimal) -> "Asset":
        return cls(
            id=str(uuid.uuid4()),
            name=name,
            type=type,
            institution=institution,
            amount=amount,
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type.value,
            "institution": self.institution,
            "amount": str(self.amount),
            "currency": self.currency,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
