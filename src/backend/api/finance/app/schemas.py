from pydantic import BaseModel
from typing import Optional


class RecordTransactionRequest(BaseModel):
    amount: str
    type: str
    category: str
    description: str
    date: Optional[str] = None


class UpdateTransactionRequest(BaseModel):
    amount: str
    type: str
    category: str
    description: str
    date: Optional[str] = None


class TransactionResponse(BaseModel):
    id: str
    amount: str
    type: str
    category: str
    description: str
    date: Optional[str] = None
