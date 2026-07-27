from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional
import uuid

from pydantic import BaseModel, ConfigDict


class TransitMode(str, Enum):
    """SPPO (regular buses) and BRT run as two independent real-time systems
    at dados.mobilidade.rio with disjoint line-code spaces — the same code
    ("22", "483", ...) can mean a different line depending on mode, so every
    tracked line must be scoped to exactly one."""

    SPPO = "sppo"
    BRT = "brt"


class TrackedLine(BaseModel):
    model_config = ConfigDict(frozen=False)

    id: str
    line_code: str
    mode: TransitMode = TransitMode.SPPO
    label: Optional[str] = None
    active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @classmethod
    def create(
        cls,
        line_code: str,
        mode: TransitMode = TransitMode.SPPO,
        label: Optional[str] = None,
        active: bool = True,
    ) -> TrackedLine:
        return cls(
            id=str(uuid.uuid4()),
            line_code=line_code,
            mode=mode,
            label=label or None,
            active=active,
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "line_code": self.line_code,
            "mode": self.mode.value,
            "label": self.label,
            "active": self.active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
