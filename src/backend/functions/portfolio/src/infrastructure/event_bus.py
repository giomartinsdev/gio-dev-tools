from typing import Callable, Type

from shared.logger import get_logger

from ..domain.events import DomainEvent

logger = get_logger(__name__)


class EventBus:
    def __init__(self):
        self._handlers: dict[Type[DomainEvent], list[Callable]] = {}

    def subscribe(self, event_type: Type[DomainEvent], handler: Callable) -> None:
        self._handlers.setdefault(event_type, []).append(handler)

    def publish(self, event: DomainEvent) -> None:
        for handler in self._handlers.get(type(event), []):
            try:
                handler(event)
            except Exception as e:
                logger.error(f"event handler failed for {type(event).__name__}: {e}", exc_info=True)


_bus = EventBus()


def get_event_bus() -> EventBus:
    return _bus
