from decimal import Decimal
from typing import Optional

from shared.transaction_manager import TransactionManager
from shared.timezone_handler import TimezoneAware

from ..domain.asset import Asset, AssetType
from ..domain.repository import AssetRepository
from .models import AssetModel

_SP = TimezoneAware("America/Sao_Paulo")


class PostgresAssetRepository(AssetRepository):
    def save(self, asset: Asset) -> None:
        with TransactionManager.get().session() as s:
            s.add(AssetModel(
                id=asset.id,
                name=asset.name,
                type=asset.type.value,
                institution=asset.institution,
                quantity=asset.quantity,
                purchase_price=asset.purchase_price,
                currency=asset.currency,
            ))

    def delete(self, asset_id: str) -> bool:
        with TransactionManager.get().session() as s:
            row = s.get(AssetModel, asset_id)
            if row is None or row.deleted_at is not None:
                return False
            row.deleted_at = _SP.now
            return True

    def find_all(self) -> list[Asset]:
        with TransactionManager.get().read_only() as s:
            rows = (
                s.query(AssetModel)
                .filter(AssetModel.deleted_at.is_(None))
                .order_by(AssetModel.created_at.asc())
                .all()
            )
            return [_to_domain(r) for r in rows]

    def find_by_id(self, asset_id: str) -> Optional[Asset]:
        with TransactionManager.get().read_only() as s:
            row = s.get(AssetModel, asset_id)
            if row is None or row.deleted_at is not None:
                return None
            return _to_domain(row)


def _to_domain(row: AssetModel) -> Asset:
    return Asset(
        id=row.id,
        name=row.name,
        type=AssetType(row.type),
        institution=row.institution,
        quantity=Decimal(str(row.quantity)),
        purchase_price=Decimal(str(row.purchase_price)),
        currency=row.currency,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )
