from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from alexapy import AlexaAPI

from .schemas import (
    AuthStatusResponse,
    AuthVerifyRequest,
    CommandRequest,
    CommandResponse,
    DeviceInfo,
)

router = APIRouter()


def _wait(request: Request):
    request.app.state._init_done.wait(timeout=30)
    if request.app.state._init_error:
        raise HTTPException(status_code=503, detail="alexa service unavailable")


def _require_auth(request: Request):
    _wait(request)
    login = request.app.state.login
    if login is None or not (login.status or {}).get("login_successful"):
        raise HTTPException(status_code=401, detail="not authenticated — complete login via /auth/verify")


@router.get("/auth/status", response_model=AuthStatusResponse)
def auth_status(request: Request):
    _wait(request)
    login = request.app.state.login
    if login is None:
        return AuthStatusResponse(authenticated=False, status={})
    status = login.status or {}
    return AuthStatusResponse(authenticated=bool(status.get("login_successful")), status=status)


@router.post("/auth/verify")
async def auth_verify(body: AuthVerifyRequest, request: Request):
    _wait(request)
    login = request.app.state.login
    if login is None:
        raise HTTPException(status_code=503, detail="service not initialised")
    if (login.status or {}).get("login_successful"):
        return {"message": "already authenticated"}

    # alexapy accepts OTP/2FA codes via login() with the verificationCode kwarg
    await login.login(data={"verificationCode": body.code, "otpCode": body.code})

    status = login.status or {}
    if not status.get("login_successful"):
        raise HTTPException(status_code=400, detail=f"verification failed: {status}")

    # Load devices now that login succeeded
    from .main import _load_devices
    await _load_devices(request.app)
    return {"message": "authenticated", "status": status}


@router.get("/devices", response_model=list[DeviceInfo])
def list_devices(request: Request):
    _require_auth(request)
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
    _require_auth(request)
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
    await alexa_api.send_sequence_command(
        "Alexa.TextCommand",
        {"text": body.text.strip(), "textType": "text"},
    )

    return CommandResponse(sent=True, text=body.text.strip(), device=device.get("accountName", ""))
