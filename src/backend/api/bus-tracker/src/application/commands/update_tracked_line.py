from typing import Optional

from pydantic import BaseModel

from ...domain.events import TrackedLineUpdated
from ...domain.repository import TrackedLineRepository
from ...domain.tracked_line import TrackedLine
from ...infrastructure.event_bus import EventBus


class UpdateTrackedLineCommand(BaseModel):
    line_id: str
    line_code: str
    label: str = ""
    active: bool = True


class UpdateTrackedLineHandler:
    def __init__(self, repo: TrackedLineRepository, bus: EventBus):
        self._repo = repo
        self._bus = bus

    def handle(self, cmd: UpdateTrackedLineCommand) -> Optional[TrackedLine]:
        if not cmd.line_code.strip():
            raise ValueError("line_code is required")

        existing = self._repo.find_by_id(cmd.line_id)
        if existing is None:
            return None

        existing.line_code = cmd.line_code.strip()
        existing.label = cmd.label.strip() or None
        existing.active = cmd.active
        self._repo.update(existing)

        self._bus.publish(TrackedLineUpdated(
            line_id=existing.id, line_code=existing.line_code, active=existing.active,
        ))

        return existing
