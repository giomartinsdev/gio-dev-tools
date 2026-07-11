from __future__ import annotations

import asyncpg

from shared.logger import get_logger

logger = get_logger(__name__)


def _admin_uri(uri: str) -> str:
    return uri.rsplit("/", 1)[0] + "/postgres"


def _db_name(uri: str) -> str:
    return uri.rsplit("/", 1)[-1]


async def ensure_db(uri: str) -> None:
    """Same pattern as worker/whatsapp/worker.py's ensure_db: this worker
    gets its own dedicated database on the shared Postgres instance, which
    SQLAlchemy's create_all alone won't create."""
    db = _db_name(uri)
    admin = await asyncpg.connect(_admin_uri(uri))
    try:
        exists = await admin.fetchval("SELECT 1 FROM pg_database WHERE datname = $1", db)
        if not exists:
            await admin.execute(f"CREATE DATABASE {db}")
            logger.info(f"created database '{db}'")
    finally:
        await admin.close()
