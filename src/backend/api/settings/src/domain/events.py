from datetime import datetime

from pydantic import BaseModel, Field


class DomainEvent(BaseModel):
    occurred_at: datetime = Field(default_factory=datetime.utcnow)


class ServiceCreated(DomainEvent):
    service_id: str = ""
    name: str = ""
    category: str = ""


class ServiceUpdated(DomainEvent):
    service_id: str = ""
    name: str = ""
    status: str = ""


class ServiceDeleted(DomainEvent):
    service_id: str = ""
