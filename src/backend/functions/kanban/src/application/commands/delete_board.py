from pydantic import BaseModel

from ...domain.events import BoardDeleted
from ...domain.repository import BoardRepository
from ...infrastructure.event_bus import EventBus


class DeleteBoardCommand(BaseModel):
    board_id: str


class DeleteBoardHandler:
    def __init__(self, repo: BoardRepository, bus: EventBus):
        self._repo = repo
        self._bus = bus

    def handle(self, cmd: DeleteBoardCommand) -> bool:
        deleted = self._repo.delete(cmd.board_id)
        if deleted:
            self._bus.publish(BoardDeleted(board_id=cmd.board_id))
        return deleted
