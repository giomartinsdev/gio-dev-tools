from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from typing import Awaitable, Callable

import aio_pika

from shared.logger import get_logger

logger = get_logger(__name__)

RECONNECT_DELAY = 5
TRIGGER_QUEUE = "value-bets-report-trigger"


class TriggerPublisher:
    def __init__(self, rabbitmq_uri: str):
        self._rabbitmq_uri = rabbitmq_uri

    async def publish(self, reason: str) -> None:
        payload = {"reason": reason, "triggered_at": datetime.now(timezone.utc).isoformat()}
        conn = await aio_pika.connect_robust(self._rabbitmq_uri)
        try:
            channel = await conn.channel()
            await channel.declare_queue(TRIGGER_QUEUE, durable=True)
            await channel.default_exchange.publish(
                aio_pika.Message(
                    body=json.dumps(payload).encode(),
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                ),
                routing_key=TRIGGER_QUEUE,
            )
        finally:
            await conn.close()
        logger.info(f"value-bets-report trigger published ({reason})")


async def consume_triggers(uri: str, on_trigger: Callable[[], Awaitable[None]]) -> None:
    while True:
        try:
            conn = await aio_pika.connect_robust(uri)
            async with conn:
                channel = await conn.channel()
                await channel.set_qos(prefetch_count=1)
                queue = await channel.declare_queue(TRIGGER_QUEUE, durable=True)
                logger.info(f"consuming {TRIGGER_QUEUE}")
                async with queue.iterator() as it:
                    async for message in it:
                        try:
                            await on_trigger()
                            await message.ack()
                        except Exception as exc:
                            logger.error(f"poison message on {TRIGGER_QUEUE}: {exc}", exc_info=True)
                            await message.nack(requeue=False)
        except Exception as exc:
            logger.error(f"{TRIGGER_QUEUE} consumer error: {exc} — reconnecting in {RECONNECT_DELAY}s")
            await asyncio.sleep(RECONNECT_DELAY)
