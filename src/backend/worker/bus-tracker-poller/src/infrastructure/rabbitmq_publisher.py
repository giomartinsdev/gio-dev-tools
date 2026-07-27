from __future__ import annotations

import json
from typing import Optional

import aio_pika

from shared.events import DomainEvent
from shared.rabbitmq_topology import DOMAIN_EXCHANGE, declare_topology


class RabbitMQPublisher:
    def __init__(self, uri: str):
        self._uri = uri
        self._connection: Optional[aio_pika.abc.AbstractRobustConnection] = None
        self._domain_exchange: Optional[aio_pika.abc.AbstractExchange] = None

    async def connect(self) -> None:
        self._connection = await aio_pika.connect_robust(self._uri)
        channel = await self._connection.channel()
        await declare_topology(channel)
        self._domain_exchange = await channel.get_exchange(DOMAIN_EXCHANGE)

    async def close(self) -> None:
        if self._connection is not None:
            await self._connection.close()

    async def publish_domain_event(self, event: DomainEvent) -> None:
        assert self._domain_exchange is not None, "publisher not connected"
        await self._domain_exchange.publish(
            aio_pika.Message(
                body=json.dumps(event.model_dump(mode="json")).encode(),
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            ),
            routing_key=event.event_type,
        )
