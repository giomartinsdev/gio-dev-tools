import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class Board(BaseModel):
    model_config = ConfigDict(frozen=False)

    id: str
    name: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @classmethod
    def create(cls, name: str) -> "Board":
        return cls(id=str(uuid.uuid4()), name=name.strip())

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
