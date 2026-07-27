from __future__ import annotations

import asyncio
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from shared.logger import get_logger
from shared.secret_manager import SecretManager
from shared.transaction_manager import TransactionConfig, TransactionManager
from src.domain.events import TrackedLineCreated, TrackedLineDeleted, TrackedLineUpdated
from src.infrastructure.event_bus import get_event_bus
from src.infrastructure.models import Base
from src.infrastructure.position_consumer import PositionConsumer
from src.infrastructure.position_repository import PositionRepository
from src.infrastructure.tracked_line_repository import PostgresTrackedLineRepository

from .router import router

logger = get_logger(__name__)

RECONNECT_DELAY = 5


def _init(app: FastAPI) -> None:
    try:
        sm = SecretManager()
        rabbitmq_uri = sm.get_secret("RABBITMQ_URI")
        TransactionManager.configure(TransactionConfig(url=sm.get_secret("DATABASE_URL")))
        Base.metadata.create_all(TransactionManager.get().engine)

        bus = get_event_bus()
        bus.subscribe(TrackedLineCreated, lambda e: logger.info(f"TrackedLineCreated id={e.line_id} line_code={e.line_code}"))
        bus.subscribe(TrackedLineUpdated, lambda e: logger.info(f"TrackedLineUpdated id={e.line_id} active={e.active}"))
        bus.subscribe(TrackedLineDeleted, lambda e: logger.info(f"TrackedLineDeleted id={e.line_id}"))

        app.state.repo = PostgresTrackedLineRepository()
        app.state.position_repo = PositionRepository()
        app.state.bus = bus
        app.state.rabbitmq_uri = rabbitmq_uri
    except Exception as e:
        app.state._init_error = e
        logger.error(f"init failed: {e}", exc_info=True)
    finally:
        app.state._init_done.set()


async def _run_consumer(app: FastAPI) -> None:
    await asyncio.to_thread(app.state._init_done.wait)
    if app.state._init_error is not None:
        return
    consumer = PositionConsumer(app.state.position_repo, app.state.sse_subs)
    await consumer.run(app.state.rabbitmq_uri)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state._init_done = threading.Event()
    app.state._init_error = None
    app.state.repo = None
    app.state.position_repo = None
    app.state.bus = None
    app.state.sse_subs: dict[str, set[asyncio.Queue]] = {}
    threading.Thread(target=_init, args=(app,), daemon=True).start()

    consumer_task = asyncio.create_task(_run_consumer(app))
    yield

    consumer_task.cancel()


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
