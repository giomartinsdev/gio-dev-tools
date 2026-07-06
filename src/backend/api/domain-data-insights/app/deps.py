import threading

from fastapi import Depends, HTTPException, Request

from src.infrastructure.read_only_repository import ReadOnlyRepository


def _ready(request: Request) -> None:
    init_done: threading.Event = request.app.state._init_done
    init_done.wait()
    if request.app.state._init_error is not None:
        raise HTTPException(status_code=503, detail="service unavailable")


def get_repo(request: Request, _: None = Depends(_ready)) -> ReadOnlyRepository:
    return request.app.state.repo
