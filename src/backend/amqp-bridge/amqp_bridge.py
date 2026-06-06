import asyncio
import json
import logging
import os

import aio_pika
import httpx

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

RABBITMQ_URI = os.environ["RABBITMQ_URI"]              
RABBITMQ_EXCHANGE = os.environ["RABBITMQ_EXCHANGE_NAME"] 
EVOLUTION_INSTANCE = os.environ["EVOLUTION_INSTANCE_NAME"]
FUNCTION_URL = os.environ["FUNCTION_URL"]            

QUEUE_NAME = "whatsapp-bridge"
ROUTING_KEY = f"{EVOLUTION_INSTANCE}.#"

RECONNECT_DELAY = 5


def routing_key_to_event(routing_key: str) -> str:
    parts = routing_key.split(".", 1)
    return parts[1].replace(".", "_").upper() if len(parts) == 2 else routing_key.upper()


async def forward(body: dict) -> None:
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(FUNCTION_URL, json=body)
        logger.info(f"forwarded {body.get('event')} → HTTP {resp.status_code}")
    except Exception as exc:
        logger.error(f"failed to forward {body.get('event')}: {exc}")
        raise


async def on_message(message: aio_pika.IncomingMessage) -> None:
    async with message.process(requeue=True):
        try:
            payload = json.loads(message.body)
        except json.JSONDecodeError:
            logger.warning(f"non-JSON message on {message.routing_key}, discarding")
            return

        if "event" not in payload:
            payload["event"] = routing_key_to_event(message.routing_key or "")

        await forward(payload)


async def consume() -> None:
    while True:
        try:
            logger.info(f"connecting to RabbitMQ")
            connection = await aio_pika.connect_robust(RABBITMQ_URI)
            async with connection:
                channel = await connection.channel()
                await channel.set_qos(prefetch_count=10)

                exchange = await channel.declare_exchange(
                    RABBITMQ_EXCHANGE,
                    aio_pika.ExchangeType.TOPIC,
                    durable=True,
                )

                queue = await channel.declare_queue(QUEUE_NAME, durable=True)
                await queue.bind(exchange, routing_key=ROUTING_KEY)

                logger.info(f"consuming queue '{QUEUE_NAME}' bound to '{ROUTING_KEY}'")
                await queue.consume(on_message)
                await asyncio.Future()  # run forever

        except Exception as exc:
            logger.error(f"connection error: {exc} — reconnecting in {RECONNECT_DELAY}s")
            await asyncio.sleep(RECONNECT_DELAY)


asyncio.run(consume())
