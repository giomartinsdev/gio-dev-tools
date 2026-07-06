from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from src.application.commands.poll_fixtures import PollFixturesCommand, PollFixturesHandler
from src.application.commands.poll_h2h import PollH2HCommand, PollH2HHandler
from src.application.commands.poll_incidents import PollIncidentsCommand, PollIncidentsHandler
from src.application.commands.poll_lineups import PollLineupsCommand, PollLineupsHandler
from src.application.commands.poll_live import PollLiveCommand, PollLiveHandler
from src.application.commands.poll_odds import PollOddsCommand, PollOddsHandler
from src.application.commands.poll_odds_best import PollOddsBestCommand, PollOddsBestHandler
from src.application.commands.poll_odds_comparison import PollOddsComparisonCommand, PollOddsComparisonHandler
from src.application.commands.poll_player_stats import PollPlayerStatsCommand, PollPlayerStatsHandler
from src.application.commands.poll_predictions import PollPredictionsCommand, PollPredictionsHandler
from src.application.commands.poll_referees import PollRefereesCommand, PollRefereesHandler
from src.application.commands.poll_standings import PollStandingsCommand, PollStandingsHandler
from src.application.commands.poll_teams import PollTeamsCommand, PollTeamsHandler
from src.application.commands.poll_venues import PollVenuesCommand, PollVenuesHandler
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


@router.post("/poll/odds-best")
async def poll_odds_best(
    client: BzzoiroClient = Depends(get_client),
    translator: BzzoiroTranslator = Depends(get_translator),
    publisher: RabbitMQPublisher = Depends(get_publisher),
):
    try:
        count = await PollOddsBestHandler(client, translator, publisher).handle(PollOddsBestCommand())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"polled": count}


@router.post("/poll/lineups")
async def poll_lineups(
    client: BzzoiroClient = Depends(get_client),
    translator: BzzoiroTranslator = Depends(get_translator),
    publisher: RabbitMQPublisher = Depends(get_publisher),
):
    try:
        count = await PollLineupsHandler(client, translator, publisher).handle(PollLineupsCommand())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"polled": count}


@router.post("/poll/h2h")
async def poll_h2h(
    client: BzzoiroClient = Depends(get_client),
    translator: BzzoiroTranslator = Depends(get_translator),
    publisher: RabbitMQPublisher = Depends(get_publisher),
):
    try:
        count = await PollH2HHandler(client, translator, publisher).handle(PollH2HCommand())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"polled": count}


@router.post("/poll/standings")
async def poll_standings(
    client: BzzoiroClient = Depends(get_client),
    translator: BzzoiroTranslator = Depends(get_translator),
    publisher: RabbitMQPublisher = Depends(get_publisher),
):
    try:
        count = await PollStandingsHandler(client, translator, publisher).handle(PollStandingsCommand())
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


@router.post("/poll/venues")
async def poll_venues(
    client: BzzoiroClient = Depends(get_client),
    translator: BzzoiroTranslator = Depends(get_translator),
    publisher: RabbitMQPublisher = Depends(get_publisher),
):
    try:
        count = await PollVenuesHandler(client, translator, publisher).handle(PollVenuesCommand())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"polled": count}


@router.post("/poll/referees")
async def poll_referees(
    client: BzzoiroClient = Depends(get_client),
    translator: BzzoiroTranslator = Depends(get_translator),
    publisher: RabbitMQPublisher = Depends(get_publisher),
):
    try:
        count = await PollRefereesHandler(client, translator, publisher).handle(PollRefereesCommand())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"polled": count}


@router.post("/poll/player-stats")
async def poll_player_stats(
    client: BzzoiroClient = Depends(get_client),
    translator: BzzoiroTranslator = Depends(get_translator),
    publisher: RabbitMQPublisher = Depends(get_publisher),
):
    try:
        count = await PollPlayerStatsHandler(client, translator, publisher).handle(PollPlayerStatsCommand())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"polled": count}


@router.post("/poll/incidents")
async def poll_incidents(
    client: BzzoiroClient = Depends(get_client),
    translator: BzzoiroTranslator = Depends(get_translator),
    publisher: RabbitMQPublisher = Depends(get_publisher),
):
    try:
        count = await PollIncidentsHandler(client, translator, publisher).handle(PollIncidentsCommand())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"polled": count}


@router.post("/resync")
async def resync(
    client: BzzoiroClient = Depends(get_client),
    translator: BzzoiroTranslator = Depends(get_translator),
    publisher: RabbitMQPublisher = Depends(get_publisher),
    checkpoints: SyncCheckpointRepository = Depends(get_checkpoints),
):
    """Force a full resync of every feed, ignoring odds/teams checkpoints.
    Every other feed has no checkpoint to bypass — they always pull their
    normal window — so this just runs all fourteen polls once."""
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
        results["odds_best"] = await PollOddsBestHandler(client, translator, publisher).handle(
            PollOddsBestCommand()
        )
        results["lineups"] = await PollLineupsHandler(client, translator, publisher).handle(
            PollLineupsCommand()
        )
        results["h2h"] = await PollH2HHandler(client, translator, publisher).handle(PollH2HCommand())
        results["standings"] = await PollStandingsHandler(client, translator, publisher).handle(
            PollStandingsCommand()
        )
        results["predictions"] = await PollPredictionsHandler(client, translator, publisher).handle(
            PollPredictionsCommand()
        )
        results["teams"] = await PollTeamsHandler(client, translator, publisher, checkpoints).handle(
            PollTeamsCommand(force=True)
        )
        results["venues"] = await PollVenuesHandler(client, translator, publisher).handle(PollVenuesCommand())
        results["referees"] = await PollRefereesHandler(client, translator, publisher).handle(
            PollRefereesCommand()
        )
        results["player_stats"] = await PollPlayerStatsHandler(client, translator, publisher).handle(
            PollPlayerStatsCommand()
        )
        results["incidents"] = await PollIncidentsHandler(client, translator, publisher).handle(
            PollIncidentsCommand()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"resynced": results}
