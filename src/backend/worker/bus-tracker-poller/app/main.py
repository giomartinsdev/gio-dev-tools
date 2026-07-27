from shared.auto_trace import install
install(["app", "src"])

import asyncio
import os
import threading
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from shared.logger import get_logger
from shared.secret_manager import SecretManager
from shared.transaction_manager import TransactionConfig, TransactionManager
from src.application.commands.poll_positions import PollPositionsCommand, PollPositionsHandler
from src.infrastructure.rabbitmq_publisher import RabbitMQPublisher
from src.infrastructure.rio_gps_client import RioGpsClient
from src.infrastructure.tracked_lines_read_repository import TrackedLinesReadRepository

from .deps import _ready
from .router import router

logger = get_logger(__name__)

POLL_SECONDS = int(os.environ.get("BUS_TRACKER_POLL_SECONDS", "20"))
RECONNECT_DELAY = 5


def _init(app: FastAPI) -> None:
    try:
        sm = SecretManager()
        rabbitmq_uri = sm.get_secret("RABBITMQ_URI")
        # tracked_lines is owned and migrated by the bus-tracker api — this
        # worker only ever reads it (no create_all here).
        TransactionManager.configure(TransactionConfig(url=sm.get_secret("DATABASE_URL")))

        app.state.client = RioGpsClient()
        app.state.tracked_lines = TrackedLinesReadRepository()
        app.state.rabbitmq_uri = rabbitmq_uri
    except Exception as e:
        app.state._init_error = e
        logger.error(f"init failed: {e}", exc_info=True)
    finally:
        app.state._init_done.set()


async def _poll_loop(handler: PollPositionsHandler) -> None:
    while True:
        try:
            count = await handler.handle(PollPositionsCommand())
            logger.info(f"positions poll completed: {count} events")
        except Exception as exc:
            logger.error(f"positions poll failed: {exc}", exc_info=True)
        await asyncio.sleep(POLL_SECONDS)


async def _run_background(app: FastAPI) -> None:
    await asyncio.to_thread(app.state._init_done.wait)
    if app.state._init_error is not None:
        return

    while True:
        try:
            publisher = RabbitMQPublisher(app.state.rabbitmq_uri)
            await publisher.connect()
            app.state.publisher = publisher
            logger.info("bus-tracker-poller connected to RabbitMQ, starting poll loop")

            handler = PollPositionsHandler(app.state.client, app.state.tracked_lines, publisher)
            await _poll_loop(handler)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            app.state.publisher = None
            logger.error(f"background loop error: {exc} — reconnecting in {RECONNECT_DELAY}s", exc_info=True)
            await asyncio.sleep(RECONNECT_DELAY)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state._init_done = threading.Event()
    app.state._init_error = None
    app.state.client = None
    app.state.tracked_lines = None
    app.state.publisher = None
    threading.Thread(target=_init, args=(app,), daemon=True).start()

    supervisor = asyncio.create_task(_run_background(app))
    yield

    supervisor.cancel()
    if app.state.publisher is not None:
        await app.state.publisher.close()


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


@app.get("/ready")
def ready(_: None = Depends(_ready)):
    return {"status": "ready"}
