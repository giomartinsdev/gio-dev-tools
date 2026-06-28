from datetime import datetime

from pydantic import BaseModel, Field


class DomainEvent(BaseModel):
    occurred_at: datetime = Field(default_factory=datetime.utcnow)


class QuotesRefreshed(DomainEvent):
    updated: list[str] = []
    failed: list[str] = []
