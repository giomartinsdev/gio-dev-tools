import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from shared.logger import get_logger
from shared.secret_manager import SecretManager
from shared.transaction_manager import TransactionConfig, TransactionManager
from src.infrastructure.read_only_repository import ReadOnlyRepository

from .router import router

logger = get_logger(__name__)


def _init(app: FastAPI) -> None:
    try:
        sm = SecretManager()
        TransactionManager.configure(TransactionConfig(url=sm.get_secret("DATABASE_URL")))
        # No create_all here: bzzoiro_data and every table in it are owned
        # and migrated by bzzoiro-acl/domain-persister — this service only
        # ever reads them (same cross-service read pattern asset-quotes
        # already uses against portfolio's `assets` table).
        app.state.repo = ReadOnlyRepository()
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
