from typing import Optional

from pydantic import BaseModel

from ...domain.service import Service, ServiceCategory, ServiceStatus
from ...domain.events import ServiceUpdated
from ...domain.repository import ServiceRepository
from ...infrastructure.event_bus import EventBus


class UpdateServiceCommand(BaseModel):
    service_id: str
    name: str
    category: str
    status: str
    secret_ref: str = ""
    notes: str = ""


class UpdateServiceHandler:
    def __init__(self, repo: ServiceRepository, bus: EventBus):
        self._repo = repo
        self._bus = bus

    def handle(self, cmd: UpdateServiceCommand) -> Optional[Service]:
        existing = self._repo.find_by_id(cmd.service_id)
        if not existing:
            return None

        if not cmd.name.strip():
            raise ValueError("name is required")
        try:
            category = ServiceCategory(cmd.category)
        except ValueError:
            raise ValueError(f"Invalid category: {cmd.category!r}")
        try:
            status = ServiceStatus(cmd.status)
        except ValueError:
            raise ValueError(f"Invalid status: {cmd.status!r}")

        updated = Service(
            id=existing.id,
            name=cmd.name.strip(),
            category=category,
            status=status,
            secret_ref=cmd.secret_ref.strip() or None,
            notes=cmd.notes.strip() or None,
        )
        self._repo.update(updated)

        self._bus.publish(ServiceUpdated(
            service_id=updated.id,
            name=updated.name,
            status=updated.status.value,
        ))

        return updated
