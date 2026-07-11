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
from src.application.generate_report import ReportGenerator
from src.application.scheduler import DailyScheduler
from src.infrastructure.config_repository import ConfigRepository
from src.infrastructure.models import create_all
from src.infrastructure.recipients_repository import RecipientsRepository
from src.infrastructure.trigger_queue import TriggerPublisher, consume_triggers
from src.infrastructure.value_bets_client import ValueBetsClient
from src.infrastructure.whatsapp_publisher import WhatsAppPublisher

from .deps import _ready
from .router import router

logger = get_logger(__name__)


def _init(app: FastAPI) -> None:
    try:
        sm = SecretManager()
        rabbitmq_uri = sm.get_secret("RABBITMQ_URI")
        database_url = sm.get_secret("DATABASE_URL")

        TransactionManager.configure(TransactionConfig(url=database_url))
        create_all(TransactionManager.get().engine)

        app.state.config_repo = ConfigRepository()
        app.state.recipients_repo = RecipientsRepository()
        app.state.trigger_publisher = TriggerPublisher(rabbitmq_uri)
        app.state.report_generator = ReportGenerator(
            value_bets_client=ValueBetsClient(),
            config_repo=app.state.config_repo,
            recipients_repo=app.state.recipients_repo,
            whatsapp_publisher=WhatsAppPublisher(rabbitmq_uri),
        )
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

    scheduler = DailyScheduler(app.state.config_repo, app.state.trigger_publisher)

    async def on_trigger() -> None:
        await app.state.report_generator.run()

    await asyncio.gather(
        consume_triggers(app.state.rabbitmq_uri, on_trigger),
        scheduler.run(),
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state._init_done = threading.Event()
    app.state._init_error = None
    app.state.config_repo = None
    app.state.recipients_repo = None
    app.state.trigger_publisher = None
    app.state.report_generator = None
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
