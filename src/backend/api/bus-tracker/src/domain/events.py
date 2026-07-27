from datetime import datetime

from pydantic import BaseModel, Field


class DomainEvent(BaseModel):
    occurred_at: datetime = Field(default_factory=datetime.utcnow)


class TrackedLineCreated(DomainEvent):
    line_id: str = ""
    line_code: str = ""


class TrackedLineUpdated(DomainEvent):
    line_id: str = ""
    line_code: str = ""
    active: bool = True


class TrackedLineDeleted(DomainEvent):
    line_id: str = ""
