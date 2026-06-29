from __future__ import annotations
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from alexapy import AlexaLogin, AlexaAPI

from shared.logger import get_logger
from shared.secret_manager import SecretManager
from .router import router

logger = get_logger(__name__)


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
    logger.info(
        f"alexa ready: {len(devices)} devices, "
        f"default={default_device and default_device.get('accountName')}"
    )


async def _async_init(app: FastAPI) -> None:
    try:
        sm = SecretManager()
        email = sm.get_secret("AMAZON_EMAIL")
        password = sm.get_secret("AMAZON_PASSWORD")
        device_name = sm.get_secret("ALEXA_DEVICE_NAME")
        app.state.device_name = device_name

        login = AlexaLogin(
            url="amazon.com",
            email=email,
            password=password,
            outputpath=lambda path: f"/data/alexa/{path}",
            debug=True,
        )
        await login.login()
        app.state.login = login

        login_status = login.status or {}
        login_successful = getattr(login, "login_successful", None)
        logger.info(f"alexa login status: {login_status}")
        logger.info(f"alexa login_successful attr: {login_successful}")
        logger.info(f"alexa login attrs: {[a for a in dir(login) if not a.startswith('_')]}")

        if login_status.get("login_successful") or login_successful:
            await _load_devices(app)
        else:
            logger.warning(f"login incomplete: {login_status}")
    except Exception as e:
        app.state._init_error = e
        logger.error(f"init failed: {e}", exc_info=True)
    finally:
        app.state._init_done.set()


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state._init_done = asyncio.Event()
    app.state._init_error = None
    app.state.login = None
    app.state.device_name = None
    app.state.devices = []
    app.state.default_device = None
    # Run in FastAPI's own event loop so alexapy's aiohttp session stays valid
    asyncio.create_task(_async_init(app))
    yield


app = FastAPI(lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.include_router(router)


@app.get("/health")
def health():
    return {"status": "ok"}
