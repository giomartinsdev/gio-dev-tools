from typing import Optional

from pydantic import BaseModel

from ...domain.card import Card, CardStatus
from ...domain.events import CardUpdated
from ...domain.repository import CardRepository
from ...infrastructure.event_bus import EventBus


class UpdateCardCommand(BaseModel):
    card_id: str
    title: str
    content: str
    status: str
    board_id: str


class UpdateCardHandler:
    def __init__(self, repo: CardRepository, bus: EventBus):
        self._repo = repo
        self._bus = bus

    def handle(self, cmd: UpdateCardCommand) -> Optional[Card]:
        card = self._repo.find_by_id(cmd.card_id)
        if not card:
            return None

        if not cmd.title.strip():
            raise ValueError("card title cannot be empty")
        try:
            status = CardStatus(cmd.status)
        except ValueError:
            raise ValueError(f"invalid status: {cmd.status}")

        card.title = cmd.title.strip()
        card.content = cmd.content
        card.status = status
        card.board_id = cmd.board_id

        self._repo.save(card)
        self._bus.publish(CardUpdated(card_id=card.id, board_id=card.board_id, title=card.title, status=card.status.value))
        return card
