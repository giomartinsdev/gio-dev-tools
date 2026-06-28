import threading
from fastapi import Depends, HTTPException, Request

from src.infrastructure.repository import PostgresBoardRepository, PostgresCardRepository
from src.infrastructure.event_bus import EventBus


def _ready(request: Request) -> None:
    init_done: threading.Event = request.app.state._init_done
    init_done.wait()
    if request.app.state._init_error is not None:
        raise HTTPException(status_code=503, detail="service unavailable")


def get_board_repo(request: Request, _: None = Depends(_ready)) -> PostgresBoardRepository:
    return request.app.state.board_repo


def get_card_repo(request: Request, _: None = Depends(_ready)) -> PostgresCardRepository:
    return request.app.state.card_repo


def get_bus(request: Request, _: None = Depends(_ready)) -> EventBus:
    return request.app.state.bus
