import threading

from fastapi import Depends, HTTPException, Request

from src.infrastructure.read_model_repository import ReadModelRepository


def _ready(request: Request) -> None:
    init_done: threading.Event = request.app.state._init_done
    init_done.wait()
    if request.app.state._init_error is not None:
        raise HTTPException(status_code=503, detail="service unavailable")


def get_read_models(request: Request, _: None = Depends(_ready)) -> ReadModelRepository:
    return request.app.state.read_models
