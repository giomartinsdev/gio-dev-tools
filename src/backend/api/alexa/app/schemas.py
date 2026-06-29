from __future__ import annotations
from pydantic import BaseModel


class CommandRequest(BaseModel):
    text: str
    device_name: str | None = None


class CommandResponse(BaseModel):
    sent: bool
    text: str
    device: str


class DeviceInfo(BaseModel):
    name: str
    type: str
    serial: str


class AuthStatusResponse(BaseModel):
    authenticated: bool
    start_url: str | None = None
    status: dict


class AuthVerifyRequest(BaseModel):
    code: str


class AuthFinalizeRequest(BaseModel):
    url: str
