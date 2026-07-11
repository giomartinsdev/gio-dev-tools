from __future__ import annotations

import json

import aio_pika

from shared.logger import get_logger

logger = get_logger(__name__)

# Same queue worker/whatsapp/worker.py's consume_outbound() consumes.
SEND_QUEUE = "whatsapp-send"


class WhatsAppPublisher:
    """Like domain-persister's WhatsAppNotifier, but the number varies per
    call (one recipients table, many numbers) instead of being fixed at
    construction."""

    def __init__(self, rabbitmq_uri: str):
        self._rabbitmq_uri = rabbitmq_uri

    async def publish(self, number: str, text: str, instance: str | None = None) -> None:
        payload: dict = {"number": number, "text": text}
        if instance:
            payload["instance"] = instance

        conn = await aio_pika.connect_robust(self._rabbitmq_uri)
        try:
            channel = await conn.channel()
            await channel.declare_queue(SEND_QUEUE, durable=True)
            await channel.default_exchange.publish(
                aio_pika.Message(
                    body=json.dumps(payload).encode(),
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                ),
                routing_key=SEND_QUEUE,
            )
        finally:
            await conn.close()
        logger.info(f"value-bets-report queued for {number}")
