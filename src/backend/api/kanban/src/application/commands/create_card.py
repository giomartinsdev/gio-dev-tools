from pydantic import BaseModel

from ...domain.card import Card, CardStatus
from ...domain.events import CardCreated
from ...domain.repository import CardRepository
from ...infrastructure.event_bus import EventBus


class CreateCardCommand(BaseModel):
    board_id: str
    title: str
    content: str = ""
    status: str = "todo"


class CreateCardHandler:
    def __init__(self, repo: CardRepository, bus: EventBus):
        self._repo = repo
        self._bus = bus

    def handle(self, cmd: CreateCardCommand) -> Card:
        if not cmd.title.strip():
            raise ValueError("card title cannot be empty")
        if not cmd.board_id:
            raise ValueError("board_id is required")
        try:
            status = CardStatus(cmd.status)
        except ValueError:
            raise ValueError(f"invalid status: {cmd.status}")

        card = Card.create(
            board_id=cmd.board_id,
            title=cmd.title,
            content=cmd.content,
            status=status,
        )
        self._repo.save(card)
        self._bus.publish(CardCreated(card_id=card.id, board_id=card.board_id, title=card.title, status=card.status.value))
        return card
