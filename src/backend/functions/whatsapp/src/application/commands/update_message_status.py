from pydantic import BaseModel

from ...domain.events import MessageStatusUpdated
from ...domain.message import MessageStatus
from ...domain.repository import MessageRepository
from ...infrastructure.event_bus import EventBus


class UpdateMessageStatusCommand(BaseModel):
    msg_id: str
    status_raw: str


class UpdateMessageStatusHandler:
    def __init__(self, msg_repo: MessageRepository, bus: EventBus):
        self._msgs = msg_repo
        self._bus = bus

    def handle(self, cmd: UpdateMessageStatusCommand) -> None:
        status = MessageStatus.from_evolution(cmd.status_raw)
        self._msgs.update_status(cmd.msg_id, status)
        self._bus.publish(MessageStatusUpdated(message_id=cmd.msg_id, status=status.value))
