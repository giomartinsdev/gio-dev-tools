from datetime import datetime

from pydantic import BaseModel, Field


class DomainEvent(BaseModel):
    occurred_at: datetime = Field(default_factory=datetime.utcnow)


class AssetCreated(DomainEvent):
    asset_id: str = ""
    name: str = ""
    type: str = ""
    quantity: str = ""
    purchase_price: str = ""


class AssetUpdated(DomainEvent):
    old_asset_id: str = ""
    new_asset_id: str = ""
    name: str = ""
    quantity: str = ""
    purchase_price: str = ""


class AssetDeleted(DomainEvent):
    asset_id: str = ""
