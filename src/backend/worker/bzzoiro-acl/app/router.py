from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from src.application.commands.poll_fixtures import PollFixturesCommand, PollFixturesHandler
from src.application.commands.poll_live import PollLiveCommand, PollLiveHandler
from src.application.commands.poll_odds import PollOddsCommand, PollOddsHandler
from src.application.commands.poll_predictions import PollPredictionsCommand, PollPredictionsHandler
from src.infrastructure.bzzoiro_client import BzzoiroClient
from src.infrastructure.rabbitmq_publisher import RabbitMQPublisher
from src.infrastructure.translator import BzzoiroTranslator

from .deps import get_client, get_publisher, get_translator

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
    client: BzzoiroClient = Depends(get_client),
    translator: BzzoiroTranslator = Depends(get_translator),
    publisher: RabbitMQPublisher = Depends(get_publisher),
):
    try:
        count = await PollOddsHandler(client, translator, publisher).handle(PollOddsCommand())
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
