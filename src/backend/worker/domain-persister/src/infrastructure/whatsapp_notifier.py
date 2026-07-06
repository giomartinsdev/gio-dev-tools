from __future__ import annotations

import json

import aio_pika

from shared.logger import get_logger

logger = get_logger(__name__)

# Same queue worker/whatsapp/worker.py's consume_outbound() consumes, and
# the same shape api/whatsapp's POST /send re-publishes — domain-persister
# isn't on the `apis` network so it can't reach that HTTP endpoint, but it's
# already on `persistence` (same network as RabbitMQ) for its own event
# consumption, so publishing directly here needs no new network access.
SEND_QUEUE = "whatsapp-send"


class WhatsAppNotifier:
    """Fires a WhatsApp text to one fixed number whenever a new value bet
    is detected. Opens a short-lived AMQP connection per notification —
    new-value-bet events are expected to be rare (one per (match, market,
    outcome) the first time its edge crosses the threshold), so this isn't
    a hot path worth keeping a persistent connection open for."""

    def __init__(self, rabbitmq_uri: str, number: str, instance: str | None = None):
        self._rabbitmq_uri = rabbitmq_uri
        self._number = number
        self._instance = instance

    async def notify(self, text: str) -> None:
        payload: dict = {"number": self._number, "text": text}
        if self._instance:
            payload["instance"] = self._instance

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
        logger.info(f"whatsapp alert queued for {self._number}")
