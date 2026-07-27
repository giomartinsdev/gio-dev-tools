import threading

from fastapi import Depends, HTTPException, Request

from src.infrastructure.rabbitmq_publisher import RabbitMQPublisher
from src.infrastructure.rio_gps_client import RioGpsClient
from src.infrastructure.tracked_lines_read_repository import TrackedLinesReadRepository


def _ready(request: Request) -> None:
    init_done: threading.Event = request.app.state._init_done
    init_done.wait()
    if request.app.state._init_error is not None:
        raise HTTPException(status_code=503, detail="service unavailable")
    if request.app.state.publisher is None:
        raise HTTPException(status_code=503, detail="rabbitmq not connected")


def get_client(request: Request, _: None = Depends(_ready)) -> RioGpsClient:
    return request.app.state.client


def get_tracked_lines(request: Request, _: None = Depends(_ready)) -> TrackedLinesReadRepository:
    return request.app.state.tracked_lines


def get_publisher(request: Request, _: None = Depends(_ready)) -> RabbitMQPublisher:
    return request.app.state.publisher
