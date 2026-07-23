from __future__ import annotations

import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from shared.logger import get_logger
from shared.secret_manager import SecretManager
from shared.transaction_manager import TransactionConfig, TransactionManager
from src.domain.events import ServiceCreated, ServiceUpdated, ServiceDeleted
from src.infrastructure.event_bus import get_event_bus
from src.infrastructure.models import Base
from src.infrastructure.repository import PostgresServiceRepository

from .router import router

logger = get_logger(__name__)


def _init(app: FastAPI) -> None:
    try:
        sm = SecretManager()
        TransactionManager.configure(TransactionConfig(url=sm.get_secret("DATABASE_URL")))
        Base.metadata.create_all(TransactionManager.get().engine)
        repo = PostgresServiceRepository()
        bus = get_event_bus()
        bus.subscribe(ServiceCreated, lambda e: logger.info(f"ServiceCreated id={e.service_id} name={e.name} category={e.category}"))
        bus.subscribe(ServiceUpdated, lambda e: logger.info(f"ServiceUpdated id={e.service_id} name={e.name} status={e.status}"))
        bus.subscribe(ServiceDeleted, lambda e: logger.info(f"ServiceDeleted id={e.service_id}"))
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
