from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from src.application.commands.poll_fixtures import PollFixturesCommand, PollFixturesHandler
from src.application.commands.poll_live import PollLiveCommand, PollLiveHandler
from src.application.commands.poll_odds import PollOddsCommand, PollOddsHandler
from src.application.commands.poll_odds_comparison import PollOddsComparisonCommand, PollOddsComparisonHandler
from src.application.commands.poll_predictions import PollPredictionsCommand, PollPredictionsHandler
from src.application.commands.poll_teams import PollTeamsCommand, PollTeamsHandler
from src.infrastructure.bzzoiro_client import BzzoiroClient
from src.infrastructure.rabbitmq_publisher import RabbitMQPublisher
from src.infrastructure.sync_checkpoint_repository import SyncCheckpointRepository
from src.infrastructure.translator import BzzoiroTranslator

from .deps import get_checkpoints, get_client, get_publisher, get_translator

router = APIRouter()


@router.post("/poll/fixtures")
async def poll_fixtures(
    client: BzzoiroClient = Depends(get_client),
    translator: BzzoiroTranslator = Depends(get_translator),
    publisher: RabbitMQPublisher = Depends(get_publisher),
):
    try:
        count = await PollFixturesHandler(client, translator, publisher).handle(PollFixturesCommand())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"polled": count}


@router.post("/poll/live")
async def poll_live(
    client: BzzoiroClient = Depends(get_client),
    translator: BzzoiroTranslator = Depends(get_translator),
    publisher: RabbitMQPublisher = Depends(get_publisher),
):
    try:
        count = await PollLiveHandler(client, translator, publisher).handle(PollLiveCommand())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"polled": count}


@router.post("/poll/odds")
async def poll_odds(
    force: bool = False,
    client: BzzoiroClient = Depends(get_client),
    translator: BzzoiroTranslator = Depends(get_translator),
    publisher: RabbitMQPublisher = Depends(get_publisher),
    checkpoints: SyncCheckpointRepository = Depends(get_checkpoints),
):
    try:
        count = await PollOddsHandler(client, translator, publisher, checkpoints).handle(
            PollOddsCommand(force=force)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"polled": count, "force": force}


@router.post("/poll/odds-comparison")
async def poll_odds_comparison(
    client: BzzoiroClient = Depends(get_client),
    translator: BzzoiroTranslator = Depends(get_translator),
    publisher: RabbitMQPublisher = Depends(get_publisher),
):
    try:
        count = await PollOddsComparisonHandler(client, translator, publisher).handle(
            PollOddsComparisonCommand()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"polled": count}


@router.post("/poll/predictions")
async def poll_predictions(
    client: BzzoiroClient = Depends(get_client),
    translator: BzzoiroTranslator = Depends(get_translator),
    publisher: RabbitMQPublisher = Depends(get_publisher),
):
    try:
        count = await PollPredictionsHandler(client, translator, publisher).handle(PollPredictionsCommand())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"polled": count}


@router.post("/poll/teams")
async def poll_teams(
    force: bool = False,
    client: BzzoiroClient = Depends(get_client),
    translator: BzzoiroTranslator = Depends(get_translator),
    publisher: RabbitMQPublisher = Depends(get_publisher),
    checkpoints: SyncCheckpointRepository = Depends(get_checkpoints),
):
    try:
        count = await PollTeamsHandler(client, translator, publisher, checkpoints).handle(
            PollTeamsCommand(force=force)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"polled": count, "force": force}


@router.post("/resync")
async def resync(
    client: BzzoiroClient = Depends(get_client),
    translator: BzzoiroTranslator = Depends(get_translator),
    publisher: RabbitMQPublisher = Depends(get_publisher),
    checkpoints: SyncCheckpointRepository = Depends(get_checkpoints),
):
    """Force a full resync of every feed, ignoring odds/teams checkpoints.
    Fixtures/live/odds-comparison/predictions have no checkpoint to bypass —
    they always pull their normal window — so this just runs all six polls
    once."""
    results: dict[str, object] = {}
    try:
        results["fixtures"] = await PollFixturesHandler(client, translator, publisher).handle(
            PollFixturesCommand()
        )
        results["live"] = await PollLiveHandler(client, translator, publisher).handle(PollLiveCommand())
        results["odds"] = await PollOddsHandler(client, translator, publisher, checkpoints).handle(
            PollOddsCommand(force=True)
        )
        results["odds_comparison"] = await PollOddsComparisonHandler(client, translator, publisher).handle(
            PollOddsComparisonCommand()
        )
        results["predictions"] = await PollPredictionsHandler(client, translator, publisher).handle(
            PollPredictionsCommand()
        )
        results["teams"] = await PollTeamsHandler(client, translator, publisher, checkpoints).handle(
            PollTeamsCommand(force=True)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"resynced": results}
