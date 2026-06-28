import threading

from fastapi import Depends, HTTPException, Request

from src.infrastructure.repository import PostgresAssetRepository
from src.infrastructure.event_bus import EventBus


def _ready(request: Request) -> None:
    init_done: threading.Event = request.app.state._init_done
    init_done.wait()
    if request.app.state._init_error is not None:
        raise HTTPException(status_code=503, detail="service unavailable")


def get_repo(request: Request, _: None = Depends(_ready)) -> PostgresAssetRepository:
    return request.app.state.repo


def get_bus(request: Request, _: None = Depends(_ready)) -> EventBus:
    return request.app.state.bus
