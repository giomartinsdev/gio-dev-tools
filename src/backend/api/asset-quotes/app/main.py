import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from shared.logger import get_logger
from shared.secret_manager import SecretManager
from shared.transaction_manager import TransactionConfig, TransactionManager
from src.domain.events import QuotesRefreshed
from src.infrastructure.brapi_client import BrapiClient
from src.infrastructure.event_bus import get_event_bus
from src.infrastructure.models import Base
from src.infrastructure.repository import PostgresQuoteEventRepository

from .router import router

logger = get_logger(__name__)


def _init(app: FastAPI) -> None:
    try:
        sm = SecretManager()
        brapi_token = sm.get_secret("BRAPI_TOKEN")
        TransactionManager.configure(TransactionConfig(url=sm.get_secret("DATABASE_URL")))
        Base.metadata.create_all(TransactionManager.get().engine)
        repo = PostgresQuoteEventRepository()
        bus = get_event_bus()
        client = BrapiClient(token=brapi_token)
        bus.subscribe(
            QuotesRefreshed,
            lambda e: logger.info(f"QuotesRefreshed updated={e.updated} failed={e.failed}"),
        )
        app.state.repo = repo
        app.state.bus = bus
        app.state.client = client
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
    app.state.client = None
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
