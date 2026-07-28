from __future__ import annotations

import asyncio
import json

import aio_pika

from shared.logger import get_logger

from ..application.commands.handle_incoming_message import HandleIncomingMessageHandler
from ..domain.message_parser import parse_evolution_payload

logger = get_logger(__name__)

QUEUE_NAME = "whatsapp-bus-eta"
ROUTING_KEY = "messages.upsert"
RECONNECT_DELAY = 5


async def consume(uri: str, exchange_name: str, handler: HandleIncomingMessageHandler) -> None:
    """Binds its own queue to the Evolution API's RabbitMQ exchange — the
    same broker api/whatsapp and worker/whatsapp already read from — filtered
    to just incoming-message events instead of persisting everything."""
    while True:
        try:
            conn = await aio_pika.connect_robust(uri)
            async with conn:
                channel = await conn.channel()
                await channel.set_qos(prefetch_count=10)
                exchange = await channel.declare_exchange(exchange_name, aio_pika.ExchangeType.TOPIC, durable=True)
                queue = await channel.declare_queue(QUEUE_NAME, durable=True)
                await queue.bind(exchange, routing_key=ROUTING_KEY)
                logger.info(f"consuming {QUEUE_NAME} bound to {exchange_name}/{ROUTING_KEY}")
                async with queue.iterator() as it:
                    async for message in it:
                        async with message.process(requeue=False):
                            try:
                                body = json.loads(message.body)
                            except json.JSONDecodeError:
                                continue
                            incoming = parse_evolution_payload(body)
                            try:
                                await handler.handle(incoming)
                            except Exception as exc:
                                logger.error(f"handle_incoming_message failed: {exc}", exc_info=True)
        except Exception as exc:
            logger.error(f"evolution consumer error: {exc} — reconnecting in {RECONNECT_DELAY}s")
            await asyncio.sleep(RECONNECT_DELAY)
