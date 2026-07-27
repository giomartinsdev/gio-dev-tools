from __future__ import annotations

from datetime import datetime
from typing import Optional
import uuid

from pydantic import BaseModel, ConfigDict


class TrackedLine(BaseModel):
    model_config = ConfigDict(frozen=False)

    id: str
    line_code: str
    label: Optional[str] = None
    active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @classmethod
    def create(cls, line_code: str, label: Optional[str] = None, active: bool = True) -> TrackedLine:
        return cls(
            id=str(uuid.uuid4()),
            line_code=line_code,
            label=label or None,
            active=active,
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "line_code": self.line_code,
            "label": self.label,
            "active": self.active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
