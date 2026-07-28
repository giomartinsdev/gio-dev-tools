from shared.auto_trace import install
install(["app", "src"])

import asyncio
import threading
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from shared.logger import get_logger
from shared.secret_manager import SecretManager
from shared.transaction_manager import TransactionConfig, TransactionManager
from src.application.commands.handle_incoming_message import HandleIncomingMessageHandler
from src.infrastructure.bus_tracker_client import BusTrackerClient
from src.infrastructure.evolution_consumer import consume
from src.infrastructure.osrm_client import OsrmClient
from src.infrastructure.state_repository import Base, PostgresConversationStateRepository
from src.infrastructure.whatsapp_sender import WhatsAppSender

from .deps import _ready

logger = get_logger(__name__)

RECONNECT_DELAY = 5


def _init(app: FastAPI) -> None:
    try:
        sm = SecretManager()
        rabbitmq_uri = sm.get_secret("RABBITMQ_URI")
        rabbitmq_exchange = sm.get_secret("RABBITMQ_EXCHANGE_NAME")
        # Owns only its own conversation-state table — tracked_lines and
        # bus_positions stay owned by the bus-tracker api, reached over HTTP.
        TransactionManager.configure(TransactionConfig(url=sm.get_secret("DATABASE_URL")))
        Base.metadata.create_all(TransactionManager.get().engine)

        app.state.state_repo = PostgresConversationStateRepository()
        app.state.bus_tracker = BusTrackerClient()
        app.state.osrm = OsrmClient()
        app.state.rabbitmq_uri = rabbitmq_uri
        app.state.rabbitmq_exchange = rabbitmq_exchange
    except Exception as e:
        app.state._init_error = e
        logger.error(f"init failed: {e}", exc_info=True)
    finally:
        app.state._init_done.set()


async def _run_background(app: FastAPI) -> None:
    await asyncio.to_thread(app.state._init_done.wait)
    if app.state._init_error is not None:
        return
    sender = WhatsAppSender(app.state.rabbitmq_uri)
    app.state.sender = sender
    handler = HandleIncomingMessageHandler(app.state.state_repo, app.state.bus_tracker, app.state.osrm, sender)
    await consume(app.state.rabbitmq_uri, app.state.rabbitmq_exchange, handler)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state._init_done = threading.Event()
    app.state._init_error = None
    app.state.state_repo = None
    app.state.bus_tracker = None
    app.state.osrm = None
    app.state.sender = None
    threading.Thread(target=_init, args=(app,), daemon=True).start()

    supervisor = asyncio.create_task(_run_background(app))
    yield
    supervisor.cancel()


app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/ready")
def ready(_: None = Depends(_ready)):
    return {"status": "ready"}
