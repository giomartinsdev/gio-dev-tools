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


def _is_authenticated(login) -> bool:
    if login is None:
        return False
    if (login.status or {}).get("login_successful"):
        return True
    return bool(getattr(login, "access_token", None))


async def _require_auth(request: Request) -> None:
    await _wait(request)
    if not _is_authenticated(request.app.state.login):
        raise HTTPException(status_code=401, detail="not authenticated")


@router.get("/auth/status", response_model=AuthStatusResponse)
async def auth_status(request: Request):
    await _wait(request)
    login = request.app.state.login
    if login is None:
        return AuthStatusResponse(authenticated=False, status={})
    authenticated = _is_authenticated(login)
    start_url = str(getattr(login, "start_url", None) or "") or None
    return AuthStatusResponse(
        authenticated=authenticated,
        start_url=start_url if not authenticated else None,
        status=login.status or {},
    )


@router.post("/auth/finalize")
async def auth_finalize(body: AuthFinalizeRequest, request: Request):
    """Complete OAuth login. body.url = full maplanding redirect URL from browser."""
    await _wait(request)
    login = request.app.state.login
    if login is None:
        raise HTTPException(status_code=503, detail="service not initialised")
    if _is_authenticated(login):
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"token exchange failed: {e}")

    # Validate session and populate login.status
    try:
        await login.test_loggedin()
    except Exception:
        pass

    status = login.status or {}
    access_token = getattr(login, "access_token", None)
    # Consider authenticated if status says so OR if we have a valid access token
    if not status.get("login_successful") and not access_token:
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
    if _is_authenticated(login):
        return {"message": "already authenticated"}

    await login.login(data={"verificationCode": body.code, "otpCode": body.code})
    if not _is_authenticated(login):
        raise HTTPException(status_code=400, detail=f"verification failed: {login.status}")

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
    text = body.text.strip()

    # Discover available methods and try in order
    api_methods = [m for m in dir(AlexaAPI) if not m.startswith("_")]
    instance_methods = [m for m in dir(alexa_api) if not m.startswith("_")]
    from shared.logger import get_logger
    _log = get_logger(__name__)
    _log.info(f"AlexaAPI class methods: {api_methods}")
    _log.info(f"alexa_api instance methods: {instance_methods}")

    if hasattr(AlexaAPI, "send_sequence_command"):
        # Static/class method form: AlexaAPI.send_sequence_command(login, device, cmd, value)
        await AlexaAPI.send_sequence_command(
            login, device, "Alexa.TextCommand",
            value={"text": text, "textType": "text"},
        )
    elif hasattr(alexa_api, "send_tts"):
        await alexa_api.send_tts(text)
    else:
        raise HTTPException(status_code=501, detail=f"no send method found. methods={instance_methods}")

    return CommandResponse(sent=True, text=body.text.strip(), device=device.get("accountName", ""))
