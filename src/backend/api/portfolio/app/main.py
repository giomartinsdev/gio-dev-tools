from __future__ import annotations

import threading
from contextlib import asynccontextmanager
from decimal import Decimal

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect, text

from shared.logger import get_logger
from shared.secret_manager import SecretManager
from shared.transaction_manager import TransactionConfig, TransactionManager
from src.domain.events import AssetCreated, AssetUpdated, AssetDeleted
from src.infrastructure.event_bus import get_event_bus
from src.infrastructure.models import Base
from src.infrastructure.repository import PostgresAssetRepository

from .router import router

logger = get_logger(__name__)


def _migrate(engine) -> None:
    insp = inspect(engine)
    if "assets" not in insp.get_table_names():
        return
    cols = {c["name"] for c in insp.get_columns("assets")}
    if "amount" in cols:
        logger.info("migration: old schema (amount) detected — recreating assets table")
        Base.metadata.drop_all(engine, tables=[Base.metadata.tables["assets"]])
        Base.metadata.create_all(engine, tables=[Base.metadata.tables["assets"]])
        return
    if "ticker" not in cols:
        logger.info("migration: adding ticker column to assets")
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE assets ADD COLUMN ticker VARCHAR"))


def _init(app: FastAPI) -> None:
    try:
        sm = SecretManager()
        TransactionManager.configure(TransactionConfig(url=sm.get_secret("DATABASE_URL")))
        Base.metadata.create_all(TransactionManager.get().engine)
        _migrate(TransactionManager.get().engine)
        repo = PostgresAssetRepository()
        bus = get_event_bus()
        bus.subscribe(AssetCreated, lambda e: logger.info(f"AssetCreated id={e.asset_id} type={e.type} qty={e.quantity} price={e.purchase_price}"))
        bus.subscribe(AssetUpdated, lambda e: logger.info(f"AssetUpdated old={e.old_asset_id} new={e.new_asset_id} qty={e.quantity} price={e.purchase_price}"))
        bus.subscribe(AssetDeleted, lambda e: logger.info(f"AssetDeleted id={e.asset_id}"))
        app.state.repo = repo
        app.state.bus = bus
    except Exception as e:
        app.state._init_error = e
        logger.error(f"init failed: {e}", exc_info=True)
    finally:
        app.state._init_done.set()


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state._init_done = threading.Event()
    app.state._init_error = None
    app.state.repo = None
    app.state.bus = None
    threading.Thread(target=_init, args=(app,), daemon=True).start()
    yield


app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)


@app.get("/health")
def health():
    return {"status": "ok"}
