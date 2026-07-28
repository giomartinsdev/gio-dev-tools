import threading

from fastapi import Depends, HTTPException, Request

from src.infrastructure.event_bus import EventBus
from src.infrastructure.position_repository import PositionRepository
from src.infrastructure.stop_repository import StopRepository
from src.infrastructure.tracked_line_repository import PostgresTrackedLineRepository


def _ready(request: Request) -> None:
    init_done: threading.Event = request.app.state._init_done
    init_done.wait()
    if request.app.state._init_error is not None:
        raise HTTPException(status_code=503, detail="service unavailable")


def get_repo(request: Request, _: None = Depends(_ready)) -> PostgresTrackedLineRepository:
    return request.app.state.repo


def get_bus(request: Request, _: None = Depends(_ready)) -> EventBus:
    return request.app.state.bus


def get_position_repo(request: Request, _: None = Depends(_ready)) -> PositionRepository:
    return request.app.state.position_repo


def get_stop_repo(request: Request, _: None = Depends(_ready)) -> StopRepository:
    return request.app.state.stop_repo
