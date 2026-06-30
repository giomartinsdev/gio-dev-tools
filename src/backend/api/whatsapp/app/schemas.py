from __future__ import annotations
from datetime import datetime
from typing import Any
from pydantic import BaseModel


class ChatSummary(BaseModel):
    remote_jid: str
    contact_name: str | None
    total_messages: int
    last_message_at: datetime
    last_message_text: str | None


class Message(BaseModel):
    id: int
    event: str
    remote_jid: str | None
    from_me: bool | None
    payload: Any
    received_at: datetime


class SendRequest(BaseModel):
    number: str
    text: str
    instance: str | None = None
