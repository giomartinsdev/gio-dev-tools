from __future__ import annotations

import asyncio
import json
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse

from src.application.commands.create_tracked_line import CreateTrackedLineCommand, CreateTrackedLineHandler
from src.application.commands.delete_tracked_line import DeleteTrackedLineCommand, DeleteTrackedLineHandler
from src.application.commands.update_tracked_line import UpdateTrackedLineCommand, UpdateTrackedLineHandler
from src.infrastructure.event_bus import EventBus
from src.infrastructure.position_repository import PositionRepository
from src.infrastructure.tracked_line_repository import PostgresTrackedLineRepository

from .deps import get_bus, get_position_repo, get_repo
from .schemas import CreateTrackedLineRequest, UpdateTrackedLineRequest

router = APIRouter()


@router.get("/lines")
def list_lines(repo: PostgresTrackedLineRepository = Depends(get_repo)):
    return [line.to_dict() for line in repo.find_all()]


@router.post("/lines", status_code=201)
def create_line(
    body: CreateTrackedLineRequest,
    repo: PostgresTrackedLineRepository = Depends(get_repo),
    bus: EventBus = Depends(get_bus),
):
    try:
        line = CreateTrackedLineHandler(repo, bus).handle(CreateTrackedLineCommand(
            line_code=body.line_code, mode=body.mode, label=body.label, active=body.active,
        ))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return line.to_dict()


@router.patch("/lines/{line_id}", status_code=200)
def update_line(
    line_id: str,
    body: UpdateTrackedLineRequest,
    repo: PostgresTrackedLineRepository = Depends(get_repo),
    bus: EventBus = Depends(get_bus),
):
    try:
        line = UpdateTrackedLineHandler(repo, bus).handle(UpdateTrackedLineCommand(
            line_id=line_id, line_code=body.line_code, mode=body.mode, label=body.label, active=body.active,
        ))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if line is None:
        raise HTTPException(status_code=404, detail="line not found")
    return line.to_dict()


@router.delete("/lines/{line_id}", status_code=200)
def delete_line(
    line_id: str,
    repo: PostgresTrackedLineRepository = Depends(get_repo),
    bus: EventBus = Depends(get_bus),
):
    deleted = DeleteTrackedLineHandler(repo, bus).handle(DeleteTrackedLineCommand(line_id=line_id))
    if not deleted:
        raise HTTPException(status_code=404, detail="line not found")
    return {"deleted": True}


@router.get("/positions/latest")
def latest_positions(line: str, mode: str = "sppo", repo: PositionRepository = Depends(get_position_repo)):
    return repo.find_latest(mode, line)


@router.get("/positions/history")
def position_history(
    line: str,
    mode: str = "sppo",
    limit: int = 50,
    offset: int = 0,
    repo: PositionRepository = Depends(get_position_repo),
):
    return repo.find_history(mode, line, limit=limit, offset=offset)


@router.get("/positions/events")
async def position_events(line: str, request: Request, mode: str = "sppo"):
    sse_subs: dict[str, set[asyncio.Queue]] = request.app.state.sse_subs
    sub_key = f"{mode}:{line}"
    q: asyncio.Queue = asyncio.Queue(maxsize=100)
    sse_subs.setdefault(sub_key, set()).add(q)

    async def stream() -> AsyncGenerator[bytes, None]:
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    msg = await asyncio.wait_for(q.get(), timeout=25.0)
                    yield f"data: {json.dumps(msg)}\n\n".encode()
                except asyncio.TimeoutError:
                    yield b": keepalive\n\n"
        finally:
            sse_subs.get(sub_key, set()).discard(q)

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
