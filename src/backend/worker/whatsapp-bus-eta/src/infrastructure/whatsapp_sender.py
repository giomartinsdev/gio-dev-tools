from __future__ import annotations

import json

import aio_pika

# Same queue the whatsapp api's POST /send publishes to — the whatsapp
# worker's outbound consumer picks it up and calls the Evolution API.
SEND_QUEUE = "whatsapp-send"


class WhatsAppSender:
    def __init__(self, rabbitmq_uri: str):
        self._uri = rabbitmq_uri

    async def send(self, number: str, text: str) -> None:
        conn = await aio_pika.connect_robust(self._uri)
        async with conn:
            channel = await conn.channel()
            await channel.declare_queue(SEND_QUEUE, durable=True)
            await channel.default_exchange.publish(
                aio_pika.Message(
                    body=json.dumps({"number": number, "text": text}).encode(),
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                ),
                routing_key=SEND_QUEUE,
            )
