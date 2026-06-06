import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict


class CardStatus(str, Enum):
    BACKLOG = "backlog"
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"


class Card(BaseModel):
    model_config = ConfigDict(frozen=False)

    id: str
    board_id: str
    title: str
    content: str = ""
    status: CardStatus = CardStatus.TODO
    position: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @classmethod
    def create(
        cls,
        board_id: str,
        title: str,
        content: str = "",
        status: CardStatus = CardStatus.TODO,
        position: int = 0,
    ) -> "Card":
        return cls(
            id=str(uuid.uuid4()),
            board_id=board_id,
            title=title.strip(),
            content=content,
            status=status,
            position=position,
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "board_id": self.board_id,
            "title": self.title,
            "content": self.content,
            "status": self.status.value,
            "position": self.position,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
