import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from shared.logger import get_logger
from shared.secret_manager import SecretManager
from shared.transaction_manager import TransactionConfig, TransactionManager
from src.domain.events import BoardCreated, BoardDeleted, CardCreated, CardDeleted, CardUpdated
from src.infrastructure.event_bus import EventBus
from src.infrastructure.models import Base
from src.infrastructure.repository import PostgresBoardRepository, PostgresCardRepository

from .router import router

logger = get_logger(__name__)


def _init(app: FastAPI) -> None:
    try:
        sm = SecretManager()
        TransactionManager.configure(TransactionConfig(url=sm.get_secret("DATABASE_URL")))
        Base.metadata.create_all(TransactionManager.get().engine)
        board_repo = PostgresBoardRepository()
        card_repo = PostgresCardRepository()
        bus = EventBus()
        bus.subscribe(BoardCreated, lambda e: logger.info(f"BoardCreated id={e.board_id} name={e.name}"))
        bus.subscribe(BoardDeleted, lambda e: logger.info(f"BoardDeleted id={e.board_id}"))
        bus.subscribe(CardCreated, lambda e: logger.info(f"CardCreated id={e.card_id} board={e.board_id}"))
        bus.subscribe(CardUpdated, lambda e: logger.info(f"CardUpdated id={e.card_id}"))
        bus.subscribe(CardDeleted, lambda e: logger.info(f"CardDeleted id={e.card_id}"))
        app.state.board_repo = board_repo
        app.state.card_repo = card_repo
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
    app.state.board_repo = None
    app.state.card_repo = None
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
