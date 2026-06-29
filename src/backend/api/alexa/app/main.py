from __future__ import annotations
import asyncio
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from alexapy import AlexaLogin, AlexaAPI

from shared.logger import get_logger
from shared.secret_manager import SecretManager
from .router import router

logger = get_logger(__name__)


async def _async_init(app: FastAPI) -> None:
    sm = SecretManager()
    email = sm.get_secret("AMAZON_EMAIL")
    password = sm.get_secret("AMAZON_PASSWORD")
    device_name = sm.get_secret("ALEXA_DEVICE_NAME")

    login = AlexaLogin(
        url="amazon.com",
        email=email,
        password=password,
        outputpath=lambda path: f"/data/alexa/{path}",
    )
    await login.login()

    app.state.login = login
    app.state.device_name = device_name
    login_status = login.status or {}
    logger.info(f"alexa login status: {login_status}")

    if not login_status.get("login_successful"):
        logger.warning("login incomplete — waiting for auth step (OTP/2FA?)")
        return

    await _load_devices(app)


async def _load_devices(app: FastAPI) -> None:
    login = app.state.login
    device_name = app.state.device_name
    devices = await AlexaAPI.get_devices(login)
    default_device = next(
        (d for d in devices if d.get("accountName") == device_name),
        devices[0] if devices else None,
    )
    app.state.devices = devices
    app.state.default_device = default_device
    logger.info(f"alexa ready: {len(devices)} devices, default={default_device and default_device.get('accountName')}")


def _init(app: FastAPI) -> None:
    try:
        asyncio.run(_async_init(app))
    except Exception as e:
        app.state._init_error = e
        logger.error(f"init failed: {e}", exc_info=True)
    finally:
        app.state._init_done.set()


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state._init_done = threading.Event()
    app.state._init_error = None
    app.state.login = None
    app.state.device_name = None
    app.state.devices = []
    app.state.default_device = None
    threading.Thread(target=_init, args=(app,), daemon=True).start()
    yield


app = FastAPI(lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.include_router(router)


@app.get("/health")
def health():
    return {"status": "ok"}
