import asyncio
import os
import threading
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from shared.logger import get_logger
from shared.secret_manager import SecretManager
from shared.transaction_manager import TransactionConfig, TransactionManager
from src.application.commands.poll_fixtures import PollFixturesCommand, PollFixturesHandler
from src.application.commands.poll_live import PollLiveCommand, PollLiveHandler
from src.application.commands.poll_odds import PollOddsCommand, PollOddsHandler
from src.application.commands.poll_predictions import PollPredictionsCommand, PollPredictionsHandler
from src.application.commands.poll_teams import PollTeamsCommand, PollTeamsHandler
from src.infrastructure.bzzoiro_client import BzzoiroClient
from src.infrastructure.identity_repository import PostgresIdentityRepository
from src.infrastructure.models import create_all
from src.infrastructure.rabbitmq_publisher import RabbitMQPublisher
from src.infrastructure.translator import BzzoiroTranslator

from .deps import _ready
from .router import router

logger = get_logger(__name__)

FIXTURES_POLL_SECONDS = int(os.environ.get("BZZOIRO_FIXTURES_POLL_SECONDS", "300"))
LIVE_POLL_SECONDS = int(os.environ.get("BZZOIRO_LIVE_POLL_SECONDS", "30"))
ODDS_POLL_SECONDS = int(os.environ.get("BZZOIRO_ODDS_POLL_SECONDS", "60"))
PREDICTIONS_POLL_SECONDS = int(os.environ.get("BZZOIRO_PREDICTIONS_POLL_SECONDS", "600"))
TEAMS_POLL_SECONDS = int(os.environ.get("BZZOIRO_TEAMS_POLL_SECONDS", "86400"))
RECONNECT_DELAY = 5


def _init(app: FastAPI) -> None:
    try:
        sm = SecretManager()
        bzzoiro_api_key = sm.get_secret("BZZOIRO_API_KEY")
        rabbitmq_uri = sm.get_secret("RABBITMQ_URI")
        TransactionManager.configure(TransactionConfig(url=sm.get_secret("DATABASE_URL")))
        create_all(TransactionManager.get().engine)

        app.state.identity_repo = PostgresIdentityRepository()
        app.state.client = BzzoiroClient(api_key=bzzoiro_api_key)
        app.state.translator = BzzoiroTranslator(app.state.identity_repo)
        app.state.rabbitmq_uri = rabbitmq_uri
    except Exception as e:
        app.state._init_error = e
        logger.error(f"init failed: {e}", exc_info=True)
    finally:
        app.state._init_done.set()


async def _poll_loop(name: str, interval: int, handler, cmd) -> None:
    while True:
        try:
            count = await handler.handle(cmd)
            logger.info(f"{name} poll completed: {count} events")
        except Exception as exc:
            logger.error(f"{name} poll failed: {exc}", exc_info=True)
        await asyncio.sleep(interval)


async def _poll_odds_loop(interval: int, handler) -> None:
    """Dedicated odds poll loop that tracks updated_after between cycles.

    Starts by checking the last captured_at from the database.
    If database is empty, fetches everything (no filter).
    """
    from sqlalchemy import text
    updated_after: Optional[datetime] = None
    try:
        def _get_last_captured():
            try:
                with TransactionManager.get().session() as s:
                    return s.execute(text("SELECT max(captured_at) FROM bzzoiro_data.odds_snapshots")).scalar()
            except Exception as e:
                logger.warning(f"Could not retrieve last captured_at: {e}")
                return None

        db_val = await asyncio.to_thread(_get_last_captured)
        if db_val:
            updated_after = db_val
            logger.info(f"odds loop starting with updated_after={updated_after} (loaded from db)")
    except Exception as exc:
        logger.warning(f"failed to load initial updated_after: {exc}")

    while True:
        try:
            count, last_updated_at = await handler.handle(PollOddsCommand(updated_after=updated_after))
            logger.info(f"odds poll completed: {count} rows, next updated_after={last_updated_at}")
            if last_updated_at is not None:
                updated_after = last_updated_at
        except Exception as exc:
            logger.error(f"odds poll failed: {exc}", exc_info=True)
        await asyncio.sleep(interval)


async def _run_background(app: FastAPI) -> None:
    await asyncio.to_thread(app.state._init_done.wait)
    if app.state._init_error is not None:
        return

    while True:
        try:
            publisher = RabbitMQPublisher(app.state.rabbitmq_uri)
            await publisher.connect()
            app.state.publisher = publisher
            logger.info("bzzoiro-acl connected to RabbitMQ, starting poll loops")

            fixtures_handler = PollFixturesHandler(app.state.client, app.state.translator, publisher)
            live_handler = PollLiveHandler(app.state.client, app.state.translator, publisher)
            odds_handler = PollOddsHandler(app.state.client, app.state.translator, publisher)
            predictions_handler = PollPredictionsHandler(app.state.client, app.state.translator, publisher)
            teams_handler = PollTeamsHandler(app.state.client, app.state.translator, publisher)
            await asyncio.gather(
                _poll_loop("fixtures", FIXTURES_POLL_SECONDS, fixtures_handler, PollFixturesCommand()),
                _poll_loop("live", LIVE_POLL_SECONDS, live_handler, PollLiveCommand()),
                _poll_odds_loop(ODDS_POLL_SECONDS, odds_handler),
                _poll_loop("predictions", PREDICTIONS_POLL_SECONDS, predictions_handler, PollPredictionsCommand()),
                _poll_loop("teams", TEAMS_POLL_SECONDS, teams_handler, PollTeamsCommand()),
            )
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
    app.state.translator = None
    app.state.identity_repo = None
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
