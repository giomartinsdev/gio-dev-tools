from datetime import datetime
from pydantic import BaseModel, Field


class DomainEvent(BaseModel):
    occurred_at: datetime = Field(default_factory=datetime.utcnow)


class StationsQueried(DomainEvent):
    count: int = 0


class LinesQueried(DomainEvent):
    count: int = 0


class LiveTripQueried(DomainEvent):
    station_id: str = ""
    line_id: str = ""
    direction: str = ""
