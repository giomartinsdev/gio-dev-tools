from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from alexapy import AlexaAPI

from .schemas import CommandRequest, CommandResponse, DeviceInfo

router = APIRouter()


def _ready(request: Request):
    request.app.state._init_done.wait(timeout=30)
    if request.app.state._init_error:
        raise HTTPException(status_code=503, detail="alexa service unavailable")


@router.get("/devices", response_model=list[DeviceInfo])
def list_devices(request: Request):
    _ready(request)
    return [
        DeviceInfo(
            name=d.get("accountName", ""),
            type=d.get("deviceType", ""),
            serial=d.get("serialNumber", ""),
        )
        for d in request.app.state.devices
    ]


@router.post("/command", response_model=CommandResponse)
async def send_command(body: CommandRequest, request: Request):
    _ready(request)
    if not body.text.strip():
        raise HTTPException(status_code=400, detail="command cannot be empty")

    login = request.app.state.login
    devices = request.app.state.devices

    if body.device_name:
        device = next((d for d in devices if d.get("accountName") == body.device_name), None)
        if device is None:
            raise HTTPException(status_code=404, detail=f"device '{body.device_name}' not found")
    else:
        device = request.app.state.default_device
        if device is None:
            raise HTTPException(status_code=503, detail="no device available")

    alexa_api = AlexaAPI(device, login)
    # Send as text command — Alexa processes text as if it were spoken
    await alexa_api.send_sequence_command(
        "Alexa.TextCommand",
        {"text": body.text.strip(), "textType": "text"},
    )

    return CommandResponse(sent=True, text=body.text.strip(), device=device.get("accountName", ""))
