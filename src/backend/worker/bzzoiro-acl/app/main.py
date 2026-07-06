import asyncio
import os
import threading
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from shared.logger import get_logger
from shared.secret_manager import SecretManager
from shared.transaction_manager import TransactionConfig, TransactionManager
from src.application.commands.poll_fixtures import PollFixturesCommand, PollFixturesHandler
from src.application.commands.poll_h2h import PollH2HCommand, PollH2HHandler
from src.application.commands.poll_lineups import PollLineupsCommand, PollLineupsHandler
from src.application.commands.poll_live import PollLiveCommand, PollLiveHandler
from src.application.commands.poll_odds import PollOddsCommand, PollOddsHandler
from src.application.commands.poll_odds_best import PollOddsBestCommand, PollOddsBestHandler
from src.application.commands.poll_odds_comparison import PollOddsComparisonCommand, PollOddsComparisonHandler
from src.application.commands.poll_predictions import PollPredictionsCommand, PollPredictionsHandler
from src.application.commands.poll_standings import PollStandingsCommand, PollStandingsHandler
from src.application.commands.poll_teams import PollTeamsCommand, PollTeamsHandler
from src.infrastructure.bzzoiro_client import BzzoiroClient
from src.infrastructure.identity_repository import PostgresIdentityRepository
from src.infrastructure.models import create_all
from src.infrastructure.rabbitmq_publisher import RabbitMQPublisher
from src.infrastructure.sync_checkpoint_repository import SyncCheckpointRepository
from src.infrastructure.translator import BzzoiroTranslator

from .deps import _ready
from .router import router

logger = get_logger(__name__)

FIXTURES_POLL_SECONDS = int(os.environ.get("BZZOIRO_FIXTURES_POLL_SECONDS", "300"))
LIVE_POLL_SECONDS = int(os.environ.get("BZZOIRO_LIVE_POLL_SECONDS", "30"))
ODDS_POLL_SECONDS = int(os.environ.get("BZZOIRO_ODDS_POLL_SECONDS", "60"))
ODDS_COMPARISON_POLL_SECONDS = int(os.environ.get("BZZOIRO_ODDS_COMPARISON_POLL_SECONDS", "90"))
ODDS_BEST_POLL_SECONDS = int(os.environ.get("BZZOIRO_ODDS_BEST_POLL_SECONDS", "60"))
LINEUPS_POLL_SECONDS = int(os.environ.get("BZZOIRO_LINEUPS_POLL_SECONDS", "300"))
H2H_POLL_SECONDS = int(os.environ.get("BZZOIRO_H2H_POLL_SECONDS", "3600"))
STANDINGS_POLL_SECONDS = int(os.environ.get("BZZOIRO_STANDINGS_POLL_SECONDS", "3600"))
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
        app.state.checkpoints = SyncCheckpointRepository()
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

            checkpoints = app.state.checkpoints
            fixtures_handler = PollFixturesHandler(app.state.client, app.state.translator, publisher)
            live_handler = PollLiveHandler(app.state.client, app.state.translator, publisher)
            odds_handler = PollOddsHandler(app.state.client, app.state.translator, publisher, checkpoints)
            odds_comparison_handler = PollOddsComparisonHandler(app.state.client, app.state.translator, publisher)
            odds_best_handler = PollOddsBestHandler(app.state.client, app.state.translator, publisher)
            lineups_handler = PollLineupsHandler(app.state.client, app.state.translator, publisher)
            h2h_handler = PollH2HHandler(app.state.client, app.state.translator, publisher)
            standings_handler = PollStandingsHandler(app.state.client, app.state.translator, publisher)
            predictions_handler = PollPredictionsHandler(app.state.client, app.state.translator, publisher)
            teams_handler = PollTeamsHandler(
                app.state.client, app.state.translator, publisher, checkpoints,
                min_resync_seconds=TEAMS_POLL_SECONDS,
            )
            await asyncio.gather(
                _poll_loop("fixtures", FIXTURES_POLL_SECONDS, fixtures_handler, PollFixturesCommand()),
                _poll_loop("live", LIVE_POLL_SECONDS, live_handler, PollLiveCommand()),
                _poll_loop("odds", ODDS_POLL_SECONDS, odds_handler, PollOddsCommand()),
                _poll_loop(
                    "odds_comparison", ODDS_COMPARISON_POLL_SECONDS,
                    odds_comparison_handler, PollOddsComparisonCommand(),
                ),
                _poll_loop("odds_best", ODDS_BEST_POLL_SECONDS, odds_best_handler, PollOddsBestCommand()),
                _poll_loop("lineups", LINEUPS_POLL_SECONDS, lineups_handler, PollLineupsCommand()),
                _poll_loop("h2h", H2H_POLL_SECONDS, h2h_handler, PollH2HCommand()),
                _poll_loop("standings", STANDINGS_POLL_SECONDS, standings_handler, PollStandingsCommand()),
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
    app.state.checkpoints = None
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
