from pydantic import BaseModel

from ...domain.events import ServiceDeleted
from ...domain.repository import ServiceRepository
from ...infrastructure.event_bus import EventBus


class DeleteServiceCommand(BaseModel):
    service_id: str


class DeleteServiceHandler:
    def __init__(self, repo: ServiceRepository, bus: EventBus):
        self._repo = repo
        self._bus = bus

    def handle(self, cmd: DeleteServiceCommand) -> bool:
        deleted = self._repo.delete(cmd.service_id)
        if deleted:
            self._bus.publish(ServiceDeleted(service_id=cmd.service_id))
        return deleted
