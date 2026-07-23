from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional
import uuid

from pydantic import BaseModel, ConfigDict


class ServiceCategory(str, Enum):
    API         = "API"
    WORKER      = "Worker"
    INTEGRATION = "Integration"
    STORAGE     = "Storage"
    OTHER       = "Other"


class ServiceStatus(str, Enum):
    CONNECTED    = "connected"
    DISCONNECTED = "disconnected"
    ERROR        = "error"


class Service(BaseModel):
    model_config = ConfigDict(frozen=False)

    id: str
    name: str
    category: ServiceCategory
    status: ServiceStatus = ServiceStatus.DISCONNECTED
    secret_ref: Optional[str] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @classmethod
    def create(
        cls,
        name: str,
        category: ServiceCategory,
        status: ServiceStatus = ServiceStatus.DISCONNECTED,
        secret_ref: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Service:
        return cls(
            id=str(uuid.uuid4()),
            name=name,
            category=category,
            status=status,
            secret_ref=secret_ref or None,
            notes=notes or None,
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category.value,
            "status": self.status.value,
            "secret_ref": self.secret_ref,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
