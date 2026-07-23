from pydantic import BaseModel

from ...domain.service import Service, ServiceCategory, ServiceStatus
from ...domain.events import ServiceCreated
from ...domain.repository import ServiceRepository
from ...infrastructure.event_bus import EventBus


class CreateServiceCommand(BaseModel):
    name: str
    category: str
    status: str = ServiceStatus.DISCONNECTED.value
    secret_ref: str = ""
    notes: str = ""


class CreateServiceHandler:
    def __init__(self, repo: ServiceRepository, bus: EventBus):
        self._repo = repo
        self._bus = bus

    def handle(self, cmd: CreateServiceCommand) -> Service:
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

        service = Service.create(
            name=cmd.name.strip(),
            category=category,
            status=status,
            secret_ref=cmd.secret_ref.strip() or None,
            notes=cmd.notes.strip() or None,
        )
        self._repo.save(service)

        self._bus.publish(ServiceCreated(
            service_id=service.id,
            name=service.name,
            category=service.category.value,
        ))

        return service
