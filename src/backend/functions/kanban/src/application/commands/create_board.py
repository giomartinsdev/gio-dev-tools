from pydantic import BaseModel

from ...domain.board import Board
from ...domain.events import BoardCreated
from ...domain.repository import BoardRepository
from ...infrastructure.event_bus import EventBus


class CreateBoardCommand(BaseModel):
    name: str


class CreateBoardHandler:
    def __init__(self, repo: BoardRepository, bus: EventBus):
        self._repo = repo
        self._bus = bus

    def handle(self, cmd: CreateBoardCommand) -> Board:
        if not cmd.name.strip():
            raise ValueError("board name cannot be empty")
        board = Board.create(name=cmd.name)
        self._repo.save(board)
        self._bus.publish(BoardCreated(board_id=board.id, name=board.name))
        return board
