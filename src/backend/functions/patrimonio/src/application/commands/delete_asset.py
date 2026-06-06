from pydantic import BaseModel

from ...domain.events import AssetDeleted
from ...domain.repository import AssetRepository
from ...infrastructure.event_bus import EventBus


class DeleteAssetCommand(BaseModel):
    asset_id: str


class DeleteAssetHandler:
    def __init__(self, repo: AssetRepository, bus: EventBus):
        self._repo = repo
        self._bus = bus

    def handle(self, cmd: DeleteAssetCommand) -> bool:
        deleted = self._repo.delete(cmd.asset_id)
        if deleted:
            self._bus.publish(AssetDeleted(asset_id=cmd.asset_id))
        return deleted
