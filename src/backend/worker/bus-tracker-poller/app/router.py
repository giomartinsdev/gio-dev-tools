from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from src.application.commands.poll_positions import PollPositionsCommand, PollPositionsHandler
from src.infrastructure.rabbitmq_publisher import RabbitMQPublisher
from src.infrastructure.rio_gps_client import RioGpsClient
from src.infrastructure.tracked_lines_read_repository import TrackedLinesReadRepository

from .deps import get_client, get_publisher, get_tracked_lines

router = APIRouter()


@router.post("/poll")
async def poll(
    client: RioGpsClient = Depends(get_client),
    tracked_lines: TrackedLinesReadRepository = Depends(get_tracked_lines),
    publisher: RabbitMQPublisher = Depends(get_publisher),
):
    try:
        count = await PollPositionsHandler(client, tracked_lines, publisher).handle(PollPositionsCommand())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"polled": count}
