from pydantic import BaseModel

from ...domain.events import TransactionDeleted
from ...domain.repository import TransactionRepository
from ...infrastructure.event_bus import EventBus


class DeleteTransactionCommand(BaseModel):
    transaction_id: str


class DeleteTransactionHandler:
    def __init__(self, repo: TransactionRepository, bus: EventBus):
        self._repo = repo
        self._bus = bus

    def handle(self, cmd: DeleteTransactionCommand) -> bool:
        deleted = self._repo.delete(cmd.transaction_id)
        if deleted:
            self._bus.publish(TransactionDeleted(transaction_id=cmd.transaction_id))
        return deleted
