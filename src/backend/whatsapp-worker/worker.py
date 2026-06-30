import asyncio
import json
import logging
import os

import aio_pika
import asyncpg
import httpx

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

RABBITMQ_URI = os.environ["RABBITMQ_URI"]
RABBITMQ_EXCHANGE = os.environ.get("RABBITMQ_EXCHANGE_NAME", "evolution")
POSTGRES_URI = os.environ["POSTGRES_URI"]
EVOLUTION_URL = os.environ.get("EVOLUTION_URL", "http://evolution-api:8080")
EVOLUTION_API_KEY = os.environ.get("EVOLUTION_API_KEY", "")
EVOLUTION_INSTANCE = os.environ.get("EVOLUTION_INSTANCE", "admin")

INBOUND_QUEUE = "whatsapp-worker"
SEND_QUEUE = "whatsapp-send"
ROUTING_KEY = "#"
RECONNECT_DELAY = 5

CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS whatsapp_messages (
    id          BIGSERIAL PRIMARY KEY,
    event       TEXT        NOT NULL,
    instance    TEXT,
    remote_jid  TEXT,
    message_id  TEXT,
    from_me     BOOLEAN,
    payload     JSONB       NOT NULL,
    received_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_wm_event    ON whatsapp_messages (event);
CREATE INDEX IF NOT EXISTS idx_wm_jid      ON whatsapp_messages (remote_jid);
CREATE INDEX IF NOT EXISTS idx_wm_received ON whatsapp_messages (received_at DESC);
"""


def _admin_uri(uri: str) -> str:
    return uri.rsplit("/", 1)[0] + "/postgres"


def _db_name(uri: str) -> str:
    return uri.rsplit("/", 1)[-1]


async def ensure_db(uri: str) -> None:
    db = _db_name(uri)
    admin = await asyncpg.connect(_admin_uri(uri))
    try:
        exists = await admin.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1", db
        )
        if not exists:
            await admin.execute(f"CREATE DATABASE {db}")
            logger.info(f"created database '{db}'")
    finally:
        await admin.close()

    conn = await asyncpg.connect(uri)
    try:
        await conn.execute(CREATE_TABLE)
        logger.info("schema ready")
    finally:
        await conn.close()


async def persist(pool: asyncpg.Pool, routing_key: str, payload: dict) -> None:
    event = payload.get("event") or routing_key.replace(".", "_").upper()
    instance = payload.get("instance")
    data = payload.get("data") or {}
    key = data.get("key") or {}
    remote_jid = key.get("remoteJid") or data.get("remoteJid")
    message_id = key.get("id") or data.get("id")
    from_me = key.get("fromMe")

    await pool.execute(
        """
        INSERT INTO whatsapp_messages
            (event, instance, remote_jid, message_id, from_me, payload)
        VALUES ($1, $2, $3, $4, $5, $6)
        """,
        event, instance, remote_jid, message_id, from_me,
        json.dumps(payload),
    )
    logger.info(f"persisted {event} | jid={remote_jid} | instance={instance}")


async def send_via_evolution(payload: dict) -> None:
    number = payload.get("number", "")
    text = payload.get("text", "")
    instance = payload.get("instance") or EVOLUTION_INSTANCE
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{EVOLUTION_URL}/message/sendText/{instance}",
            json={"number": number, "text": text},
            headers={"apikey": EVOLUTION_API_KEY},
            timeout=30.0,
        )
        resp.raise_for_status()
    logger.info(f"sent message | number={number} | instance={instance}")


async def consume_inbound(pool: asyncpg.Pool) -> None:
    while True:
        try:
            logger.info("inbound: connecting to RabbitMQ")
            conn = await aio_pika.connect_robust(RABBITMQ_URI)
            async with conn:
                channel = await conn.channel()
                await channel.set_qos(prefetch_count=20)
                exchange = await channel.declare_exchange(
                    RABBITMQ_EXCHANGE, aio_pika.ExchangeType.TOPIC, durable=True
                )
                queue = await channel.declare_queue(INBOUND_QUEUE, durable=True)
                await queue.bind(exchange, routing_key=ROUTING_KEY)
                logger.info(f"inbound: consuming queue '{INBOUND_QUEUE}'")
                async with queue.iterator() as it:
                    async for message in it:
                        async with message.process(requeue=True):
                            try:
                                body = json.loads(message.body)
                            except json.JSONDecodeError:
                                logger.warning(f"non-JSON on {message.routing_key}, discarding")
                                return
                            await persist(pool, message.routing_key or "", body)
        except Exception as exc:
            logger.error(f"inbound error: {exc} — reconnecting in {RECONNECT_DELAY}s")
            await asyncio.sleep(RECONNECT_DELAY)


async def consume_outbound() -> None:
    while True:
        try:
            logger.info("outbound: connecting to RabbitMQ")
            conn = await aio_pika.connect_robust(RABBITMQ_URI)
            async with conn:
                channel = await conn.channel()
                await channel.set_qos(prefetch_count=5)
                queue = await channel.declare_queue(SEND_QUEUE, durable=True)
                logger.info(f"outbound: consuming queue '{SEND_QUEUE}'")
                async with queue.iterator() as it:
                    async for message in it:
                        async with message.process(requeue=True):
                            try:
                                body = json.loads(message.body)
                                await send_via_evolution(body)
                            except Exception as exc:
                                logger.error(f"send failed: {exc}")
        except Exception as exc:
            logger.error(f"outbound error: {exc} — reconnecting in {RECONNECT_DELAY}s")
            await asyncio.sleep(RECONNECT_DELAY)


async def main() -> None:
    await ensure_db(POSTGRES_URI)
    pool = await asyncpg.create_pool(POSTGRES_URI, min_size=2, max_size=10)
    try:
        await asyncio.gather(consume_inbound(pool), consume_outbound())
    finally:
        await pool.close()


asyncio.run(main())
