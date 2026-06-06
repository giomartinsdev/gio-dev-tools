from decimal import Decimal, InvalidOperation

from pydantic import BaseModel

from ...domain.asset import Asset, AssetType
from ...domain.events import AssetCreated
from ...domain.repository import AssetRepository
from ...infrastructure.event_bus import EventBus


class CreateAssetCommand(BaseModel):
    name: str
    type: str
    institution: str
    quantity: str
    purchase_price: str


class CreateAssetHandler:
    def __init__(self, repo: AssetRepository, bus: EventBus):
        self._repo = repo
        self._bus = bus

    def handle(self, cmd: CreateAssetCommand) -> Asset:
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

        asset = Asset.create(
            name=cmd.name.strip(),
            type=asset_type,
            institution=cmd.institution.strip(),
            quantity=quantity,
            purchase_price=purchase_price,
        )
        self._repo.save(asset)

        self._bus.publish(AssetCreated(
            asset_id=asset.id,
            name=asset.name,
            type=asset.type.value,
            quantity=str(asset.quantity),
            purchase_price=str(asset.purchase_price),
        ))

        return asset
