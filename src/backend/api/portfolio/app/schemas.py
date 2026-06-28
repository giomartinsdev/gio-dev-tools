from pydantic import BaseModel
from typing import Optional


class CreateAssetRequest(BaseModel):
    name: str
    type: str
    institution: str
    quantity: str
    purchase_price: str
    ticker: str = ""


class UpdateAssetRequest(BaseModel):
    name: str
    type: str
    institution: str
    quantity: str
    purchase_price: str
    ticker: str = ""
