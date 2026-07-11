import threading

from fastapi import Depends, HTTPException, Request

from src.infrastructure.config_repository import ConfigRepository
from src.infrastructure.recipients_repository import RecipientsRepository
from src.infrastructure.trigger_queue import TriggerPublisher


def _ready(request: Request) -> None:
    init_done: threading.Event = request.app.state._init_done
    init_done.wait()
    if request.app.state._init_error is not None:
        raise HTTPException(status_code=503, detail="service unavailable")


def get_config_repo(request: Request, _: None = Depends(_ready)) -> ConfigRepository:
    return request.app.state.config_repo


def get_recipients_repo(request: Request, _: None = Depends(_ready)) -> RecipientsRepository:
    return request.app.state.recipients_repo


def get_trigger_publisher(request: Request, _: None = Depends(_ready)) -> TriggerPublisher:
    return request.app.state.trigger_publisher
