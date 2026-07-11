from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from src.infrastructure.config_repository import ConfigRepository
from src.infrastructure.recipients_repository import RecipientsRepository
from src.infrastructure.trigger_queue import TriggerPublisher

from .deps import get_config_repo, get_recipients_repo, get_trigger_publisher

router = APIRouter()


class ConfigUpdate(BaseModel):
    send_time: str
    reference_day_offset: int
    enabled: bool


class RecipientCreate(BaseModel):
    phone_number: str
    name: Optional[str] = None


class RecipientUpdate(BaseModel):
    active: bool


@router.get("/config")
def get_config(repo: ConfigRepository = Depends(get_config_repo)):
    return repo.get()


@router.put("/config")
def put_config(body: ConfigUpdate, repo: ConfigRepository = Depends(get_config_repo)):
    return repo.update(
        send_time=body.send_time,
        reference_day_offset=body.reference_day_offset,
        enabled=body.enabled,
    )


@router.get("/recipients")
def list_recipients(repo: RecipientsRepository = Depends(get_recipients_repo)):
    return repo.list_all()


@router.post("/recipients")
def create_recipient(body: RecipientCreate, repo: RecipientsRepository = Depends(get_recipients_repo)):
    return repo.create(phone_number=body.phone_number, name=body.name)


@router.delete("/recipients/{recipient_id}")
def delete_recipient(recipient_id: int, repo: RecipientsRepository = Depends(get_recipients_repo)):
    repo.delete(recipient_id)
    return {"status": "deleted"}


@router.patch("/recipients/{recipient_id}")
def update_recipient(
    recipient_id: int, body: RecipientUpdate, repo: RecipientsRepository = Depends(get_recipients_repo),
):
    result = repo.set_active(recipient_id, body.active)
    if result is None:
        raise HTTPException(status_code=404, detail="recipient not found")
    return result


@router.post("/trigger")
async def trigger_now(publisher: TriggerPublisher = Depends(get_trigger_publisher)):
    await publisher.publish(reason="manual")
    return {"status": "queued"}
