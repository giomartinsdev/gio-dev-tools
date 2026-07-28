import threading
from typing import Optional

from pydantic import BaseModel

from shared.logger import get_logger

from ...domain.events import TrackedLineCreated
from ...domain.repository import TrackedLineRepository
from ...domain.tracked_line import TrackedLine, TransitMode
from ...infrastructure.event_bus import EventBus
from ...infrastructure.gtfs_stops_importer import fetch_directions_for_line
from ...infrastructure.stop_repository import StopRepository

logger = get_logger(__name__)


class CreateTrackedLineCommand(BaseModel):
    line_code: str
    mode: str = TransitMode.SPPO.value
    label: str = ""
    active: bool = True


class CreateTrackedLineHandler:
    def __init__(self, repo: TrackedLineRepository, bus: EventBus, stop_repo: Optional[StopRepository] = None):
        self._repo = repo
        self._bus = bus
        self._stop_repo = stop_repo

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

        if self._stop_repo is not None:
            threading.Thread(
                target=_import_stops_best_effort,
                args=(self._stop_repo, line.mode.value, line.line_code),
                daemon=True,
            ).start()

        return line


def _import_stops_best_effort(stop_repo: StopRepository, mode: str, line_code: str) -> None:
    try:
        directions = fetch_directions_for_line(line_code)
        stop_repo.replace_directions_for_line(mode, line_code, directions)
        logger.info(f"imported {len(directions)} GTFS directions for {mode}:{line_code}")
    except Exception as e:
        logger.error(f"GTFS stop import failed for {mode}:{line_code}: {e}", exc_info=True)
