from __future__ import annotations
import asyncio
from urllib.parse import parse_qs, urlparse

from fastapi import APIRouter, HTTPException, Request
from alexapy import AlexaAPI

from .schemas import (
    AuthFinalizeRequest,
    AuthStatusResponse,
    AuthVerifyRequest,
    CommandRequest,
    CommandResponse,
    DeviceInfo,
)

router = APIRouter()


async def _wait(request: Request) -> None:
    try:
        await asyncio.wait_for(request.app.state._init_done.wait(), timeout=30)
    except asyncio.TimeoutError:
        raise HTTPException(status_code=503, detail="init timeout")
    if request.app.state._init_error:
        raise HTTPException(status_code=503, detail="alexa service unavailable")


async def _require_auth(request: Request) -> None:
    await _wait(request)
    login = request.app.state.login
    if login is None or not (login.status or {}).get("login_successful"):
        raise HTTPException(status_code=401, detail="not authenticated")


@router.get("/auth/status", response_model=AuthStatusResponse)
async def auth_status(request: Request):
    await _wait(request)
    login = request.app.state.login
    if login is None:
        return AuthStatusResponse(authenticated=False, status={})
    status = login.status or {}
    start_url = getattr(login, "start_url", None)
    return AuthStatusResponse(
        authenticated=bool(status.get("login_successful")),
        start_url=start_url if not status.get("login_successful") else None,
        status=status,
    )


@router.post("/auth/finalize")
async def auth_finalize(body: AuthFinalizeRequest, request: Request):
    """Complete OAuth login. body.url = full maplanding redirect URL from browser."""
    await _wait(request)
    login = request.app.state.login
    if login is None:
        raise HTTPException(status_code=503, detail="service not initialised")
    if (login.status or {}).get("login_successful"):
        return {"message": "already authenticated"}

    # Extract auth code from the redirect URL
    parsed = urlparse(body.url)
    params = parse_qs(parsed.query)
    code = (
        params.get("openid.oa2.authorization_code", [None])[0]
        or params.get("code", [None])[0]
    )
    if not code:
        raise HTTPException(status_code=400, detail="no auth code found in URL — paste the full URL from the browser address bar after login")

    # Exchange the auth code for session cookies
    login.authorization_code = code
    try:
        await login.exchange_token_for_cookies()
    except Exception:
        # Some alexapy versions use finalize_login instead
        try:
            await login.finalize_login(code=code)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"token exchange failed: {e}")

    status = login.status or {}
    if not status.get("login_successful"):
        raise HTTPException(status_code=400, detail=f"login failed after exchange: {status}")

    from .main import _load_devices
    await _load_devices(request.app)
    return {"message": "authenticated"}


@router.post("/auth/verify")
async def auth_verify(body: AuthVerifyRequest, request: Request):
    """Submit OTP/2FA code if Amazon requested one."""
    await _wait(request)
    login = request.app.state.login
    if login is None:
        raise HTTPException(status_code=503, detail="service not initialised")
    if (login.status or {}).get("login_successful"):
        return {"message": "already authenticated"}

    await login.login(data={"verificationCode": body.code, "otpCode": body.code})
    status = login.status or {}
    if not status.get("login_successful"):
        raise HTTPException(status_code=400, detail=f"verification failed: {status}")

    from .main import _load_devices
    await _load_devices(request.app)
    return {"message": "authenticated"}


@router.get("/devices", response_model=list[DeviceInfo])
async def list_devices(request: Request):
    await _require_auth(request)
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
    await _require_auth(request)
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
