import os
from contextlib import contextmanager
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from ..domain.asset import Asset, AssetType
from ..domain.repository import AssetRepository
from .models import Base, AssetModel

_engine = create_engine(os.environ["DATABASE_URL"])


@contextmanager
def _session():
    with Session(_engine) as session, session.begin():
        yield session


def migrate() -> None:
    Base.metadata.create_all(_engine)


class PostgresAssetRepository(AssetRepository):
    def save(self, asset: Asset) -> None:
        with _session() as s:
            existing = s.get(AssetModel, asset.id)
            if existing:
                existing.name = asset.name
                existing.type = asset.type.value
                existing.institution = asset.institution
                existing.amount = asset.amount
                existing.updated_at = datetime.now(timezone.utc)
            else:
                s.add(AssetModel(
                    id=asset.id,
                    name=asset.name,
                    type=asset.type.value,
                    institution=asset.institution,
                    amount=asset.amount,
                    currency=asset.currency,
                ))

    def delete(self, asset_id: str) -> bool:
        with _session() as s:
            row = s.get(AssetModel, asset_id)
            if row is None or row.deleted_at is not None:
                return False
            row.deleted_at = datetime.now(timezone.utc)
            row.updated_at = datetime.now(timezone.utc)
            return True

    def find_all(self) -> list[Asset]:
        with _session() as s:
            rows = (
                s.query(AssetModel)
                .filter(AssetModel.deleted_at.is_(None))
                .order_by(AssetModel.created_at.asc())
                .all()
            )
            return [_to_domain(r) for r in rows]

    def find_by_id(self, asset_id: str) -> Optional[Asset]:
        with _session() as s:
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
        amount=Decimal(str(row.amount)),
        currency=row.currency,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )
