from pydantic import BaseModel

from ...domain.events import TrackedLineCreated
from ...domain.repository import TrackedLineRepository
from ...domain.tracked_line import TrackedLine, TransitMode
from ...infrastructure.event_bus import EventBus


class CreateTrackedLineCommand(BaseModel):
    line_code: str
    mode: str = TransitMode.SPPO.value
    label: str = ""
    active: bool = True


class CreateTrackedLineHandler:
    def __init__(self, repo: TrackedLineRepository, bus: EventBus):
        self._repo = repo
        self._bus = bus

    def handle(self, cmd: CreateTrackedLineCommand) -> TrackedLine:
        if not cmd.line_code.strip():
            raise ValueError("line_code is required")
        try:
            mode = TransitMode(cmd.mode)
        except ValueError:
            raise ValueError(f"Invalid mode: {cmd.mode!r}")

        line = TrackedLine.create(
            line_code=cmd.line_code.strip(),
            mode=mode,
            label=cmd.label.strip() or None,
            active=cmd.active,
        )
        self._repo.save(line)

        self._bus.publish(TrackedLineCreated(line_id=line.id, line_code=line.line_code))

        return line
