from shared.auto_trace import install
install(["app"])

import asyncio
import json
from contextlib import asynccontextmanager

import aio_pika
import asyncpg
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from shared.logger import get_logger
from shared.secret_manager import SecretManager
from .router import router

logger = get_logger(__name__)

_sse_subs: set[asyncio.Queue] = set()


def _load_config() -> dict:
    sm = SecretManager()
    return {
        "postgres_uri": sm.get_secret("POSTGRES_URI"),
        "rabbitmq_uri": sm.get_secret("RABBITMQ_URI"),
        "rabbitmq_exchange": sm.get_secret("RABBITMQ_EXCHANGE_NAME"),
        "evolution_api_key": sm.get_secret("EVOLUTION_API_KEY"),
        "evolution_instance": sm.get_secret("EVOLUTION_INSTANCE"),
        "evolution_url": sm.get_secret("EVOLUTION_URL"),
    }


async def _broadcast_loop(rabbitmq_uri: str, rabbitmq_exchange: str) -> None:
    """Subscribe to the evolution exchange and fan out every event to SSE clients."""
    while True:
        try:
            conn = await aio_pika.connect_robust(rabbitmq_uri)
            async with conn:
                ch = await conn.channel()
                exchange = await ch.declare_exchange(
                    rabbitmq_exchange, aio_pika.ExchangeType.TOPIC, durable=True
                )
                q = await ch.declare_queue("", exclusive=True, auto_delete=True)
                await q.bind(exchange, routing_key="#")
                logger.info("SSE broadcast loop connected")
                async with q.iterator() as it:
                    async for msg in it:
                        async with msg.process():
                            try:
                                body = json.loads(msg.body)
                            except json.JSONDecodeError:
                                continue
                            dead = set()
                            for sub in list(_sse_subs):
                                try:
                                    sub.put_nowait(body)
                                except asyncio.QueueFull:
                                    dead.add(sub)
                            _sse_subs.difference_update(dead)
        except Exception as exc:
            logger.error(f"broadcast loop error: {exc} — retrying in 5s")
            await asyncio.sleep(5)


@asynccontextmanager
async def lifespan(app: FastAPI):
    cfg = _load_config()
    app.state.pg = await asyncpg.create_pool(cfg["postgres_uri"], min_size=2, max_size=10)
    app.state.mq_uri = cfg["rabbitmq_uri"]
    app.state.evolution_api_key = cfg["evolution_api_key"]
    app.state.evolution_instance = cfg["evolution_instance"]
    app.state.evolution_url = cfg["evolution_url"]
    app.state.sse_subs = _sse_subs
    asyncio.create_task(_broadcast_loop(cfg["rabbitmq_uri"], cfg["rabbitmq_exchange"]))
    yield
    await app.state.pg.close()


app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)
app.include_router(router)


@app.get("/health")
def health():
    return {"status": "ok"}
