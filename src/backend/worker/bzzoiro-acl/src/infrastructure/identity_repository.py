from __future__ import annotations

import uuid
from uuid import UUID

from sqlalchemy import text

from shared.transaction_manager import TransactionManager

from ..domain.repository import IdentityRepository
from .models import SCHEMA

_SELECT = text(f"""
    SELECT canonical_id FROM {SCHEMA}.provider_mappings
    WHERE provider = :provider AND provider_ref = :provider_ref AND entity_type = :entity_type
""")

_INSERT = text(f"""
    INSERT INTO {SCHEMA}.provider_mappings (provider, provider_ref, entity_type, canonical_id)
    VALUES (:provider, :provider_ref, :entity_type, :canonical_id)
    ON CONFLICT (provider, provider_ref, entity_type) DO NOTHING
""")


class PostgresIdentityRepository(IdentityRepository):
    def get_or_create(self, provider: str, provider_ref: str, entity_type: str) -> UUID:
        params = {"provider": provider, "provider_ref": provider_ref, "entity_type": entity_type}
        with TransactionManager.get().session() as s:
            row = s.execute(_SELECT, params).fetchone()
            if row is not None:
                return UUID(str(row.canonical_id))

            canonical_id = uuid.uuid4()
            s.execute(_INSERT, {**params, "canonical_id": str(canonical_id)})
            row = s.execute(_SELECT, params).fetchone()
            return UUID(str(row.canonical_id))
