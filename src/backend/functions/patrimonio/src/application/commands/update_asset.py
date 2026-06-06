from decimal import Decimal, InvalidOperation
from typing import Optional

from pydantic import BaseModel

from ...domain.asset import Asset, AssetType
from ...domain.events import AssetUpdated
from ...domain.repository import AssetRepository
from ...infrastructure.event_bus import EventBus


class UpdateAssetCommand(BaseModel):
    asset_id: str
    name: str
    type: str
    institution: str
    amount: str


class UpdateAssetHandler:
    def __init__(self, repo: AssetRepository, bus: EventBus):
        self._repo = repo
        self._bus = bus

    def handle(self, cmd: UpdateAssetCommand) -> Optional[Asset]:
        asset = self._repo.find_by_id(cmd.asset_id)
        if not asset:
            return None

        if not cmd.name.strip():
            raise ValueError("name is required")
        if not cmd.institution.strip():
            raise ValueError("institution is required")
        try:
            amount = Decimal(cmd.amount)
        except InvalidOperation:
            raise ValueError(f"Invalid amount: {cmd.amount!r}")
        try:
            asset_type = AssetType(cmd.type)
        except ValueError:
            raise ValueError(f"Invalid type: {cmd.type!r}")

        asset.name = cmd.name.strip()
        asset.type = asset_type
        asset.institution = cmd.institution.strip()
        asset.amount = amount
        self._repo.save(asset)

        self._bus.publish(AssetUpdated(
            asset_id=asset.id,
            name=asset.name,
            amount=str(asset.amount),
        ))

        return asset
