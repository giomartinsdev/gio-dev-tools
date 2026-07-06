import asyncio
import os
import threading
from contextlib import asynccontextmanager
from decimal import Decimal

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from shared.logger import get_logger
from shared.secret_manager import SecretManager
from shared.transaction_manager import TransactionConfig, TransactionManager
from src.application.project_domain_event import ProjectDomainEventHandler
from src.application.project_insight import ProjectInsightHandler
from src.application.value_bet_detector import ValueBetDetector
from src.infrastructure.event_store_repository import EventStoreRepository
from src.infrastructure.models import create_all
from src.infrastructure.rabbitmq_consumer import run_consumers
from src.infrastructure.read_model_repository import ReadModelRepository

from .deps import _ready
from .router import router

logger = get_logger(__name__)

RECONNECT_DELAY = 5
VALUE_BET_EDGE_THRESHOLD = Decimal(os.environ.get("VALUE_BET_EDGE_THRESHOLD", "0.05"))


def _init(app: FastAPI) -> None:
    try:
        sm = SecretManager()
        rabbitmq_uri = sm.get_secret("RABBITMQ_URI")
        TransactionManager.configure(TransactionConfig(url=sm.get_secret("DATABASE_URL")))
        create_all(TransactionManager.get().engine)

        app.state.read_models = ReadModelRepository()
        app.state.event_store = EventStoreRepository()
        app.state.value_bet_detector = ValueBetDetector(app.state.read_models, VALUE_BET_EDGE_THRESHOLD)
        app.state.rabbitmq_uri = rabbitmq_uri
    except Exception as e:
        app.state._init_error = e
        logger.error(f"init failed: {e}", exc_info=True)
    finally:
        app.state._init_done.set()


async def _run_background(app: FastAPI) -> None:
    await asyncio.to_thread(app.state._init_done.wait)
    if app.state._init_error is not None:
        return
    projector = ProjectDomainEventHandler(app.state.read_models, app.state.value_bet_detector)
    insight_handler = ProjectInsightHandler(app.state.read_models, app.state.value_bet_detector)
    await run_consumers(app.state.rabbitmq_uri, app.state.event_store, projector, insight_handler)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state._init_done = threading.Event()
    app.state._init_error = None
    app.state.read_models = None
    app.state.event_store = None
    app.state.value_bet_detector = None
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
app.include_router(router)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/ready")
def ready(_: None = Depends(_ready)):
    return {"status": "ready"}
