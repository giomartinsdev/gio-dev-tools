from pydantic import BaseModel

from ...domain.events import TrackedLineDeleted
from ...domain.repository import TrackedLineRepository
from ...infrastructure.event_bus import EventBus


class DeleteTrackedLineCommand(BaseModel):
    line_id: str


class DeleteTrackedLineHandler:
    def __init__(self, repo: TrackedLineRepository, bus: EventBus):
        self._repo = repo
        self._bus = bus

    def handle(self, cmd: DeleteTrackedLineCommand) -> bool:
        deleted = self._repo.delete(cmd.line_id)
        if deleted:
            self._bus.publish(TrackedLineDeleted(line_id=cmd.line_id))
        return deleted
