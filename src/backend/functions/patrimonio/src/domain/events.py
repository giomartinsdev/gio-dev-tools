from datetime import datetime

from pydantic import BaseModel, Field


class DomainEvent(BaseModel):
    occurred_at: datetime = Field(default_factory=datetime.utcnow)


class AssetCreated(DomainEvent):
    asset_id: str = ""
    name: str = ""
    type: str = ""
    amount: str = ""


class AssetUpdated(DomainEvent):
    asset_id: str = ""
    name: str = ""
    amount: str = ""


class AssetDeleted(DomainEvent):
    asset_id: str = ""
