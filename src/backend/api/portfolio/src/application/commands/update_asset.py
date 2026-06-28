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
    quantity: str
    purchase_price: str
    ticker: str = ""


class UpdateAssetHandler:
    def __init__(self, repo: AssetRepository, bus: EventBus):
        self._repo = repo
        self._bus = bus

    def handle(self, cmd: UpdateAssetCommand) -> Optional[Asset]:
        original = self._repo.find_by_id(cmd.asset_id)
        if not original:
            return None

        if not cmd.name.strip():
            raise ValueError("name is required")
        if not cmd.institution.strip():
            raise ValueError("institution is required")
        try:
            quantity = Decimal(cmd.quantity)
        except InvalidOperation:
            raise ValueError(f"Invalid quantity: {cmd.quantity!r}")
        try:
            purchase_price = Decimal(cmd.purchase_price)
        except InvalidOperation:
            raise ValueError(f"Invalid purchase_price: {cmd.purchase_price!r}")
        try:
            asset_type = AssetType(cmd.type)
        except ValueError:
            raise ValueError(f"Invalid type: {cmd.type!r}")

        # Immutable ledger: soft-delete the original, insert a new entry
        self._repo.delete(cmd.asset_id)

        new_asset = Asset.create(
            name=cmd.name.strip(),
            type=asset_type,
            institution=cmd.institution.strip(),
            quantity=quantity,
            purchase_price=purchase_price,
            ticker=cmd.ticker.strip().upper() or None,
        )
        self._repo.save(new_asset)

        self._bus.publish(AssetUpdated(
            old_asset_id=cmd.asset_id,
            new_asset_id=new_asset.id,
            name=new_asset.name,
            quantity=str(new_asset.quantity),
            purchase_price=str(new_asset.purchase_price),
        ))

        return new_asset
