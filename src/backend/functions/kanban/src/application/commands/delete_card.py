from pydantic import BaseModel

from ...domain.events import CardDeleted
from ...domain.repository import CardRepository
from ...infrastructure.event_bus import EventBus


class DeleteCardCommand(BaseModel):
    card_id: str


class DeleteCardHandler:
    def __init__(self, repo: CardRepository, bus: EventBus):
        self._repo = repo
        self._bus = bus

    def handle(self, cmd: DeleteCardCommand) -> bool:
        deleted = self._repo.delete(cmd.card_id)
        if deleted:
            self._bus.publish(CardDeleted(card_id=cmd.card_id))
        return deleted
