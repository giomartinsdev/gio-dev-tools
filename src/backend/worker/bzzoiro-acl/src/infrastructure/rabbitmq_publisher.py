from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

import aio_pika

from shared.events import DomainEvent, EventMeta, RawFeedReceived
from shared.rabbitmq_topology import DOMAIN_EXCHANGE, INGESTION_EXCHANGE, declare_topology

PRODUCER = "acl.bzzoiro"


class RabbitMQPublisher:
    def __init__(self, uri: str):
        self._uri = uri
        self._connection: Optional[aio_pika.abc.AbstractRobustConnection] = None
        self._ingestion_exchange: Optional[aio_pika.abc.AbstractExchange] = None
        self._domain_exchange: Optional[aio_pika.abc.AbstractExchange] = None

    async def connect(self) -> None:
        self._connection = await aio_pika.connect_robust(self._uri)
        channel = await self._connection.channel()
        await declare_topology(channel)
        self._ingestion_exchange = await channel.get_exchange(INGESTION_EXCHANGE)
        self._domain_exchange = await channel.get_exchange(DOMAIN_EXCHANGE)

    async def close(self) -> None:
        if self._connection is not None:
            await self._connection.close()

    async def publish_raw(
        self,
        feed_type: str,
        provider_ref: str,
        payload: dict,
        correlation_id: Optional[UUID] = None,
    ) -> None:
        assert self._ingestion_exchange is not None, "publisher not connected"
        event = RawFeedReceived(
            meta=EventMeta(
                occurred_at=datetime.now(timezone.utc),
                producer=PRODUCER,
                correlation_id=correlation_id or uuid4(),
            ),
            source="bzzoiro",
            feed_type=feed_type,
            provider_ref=provider_ref,
            payload=payload,
        )
        await self._ingestion_exchange.publish(
            aio_pika.Message(
                body=json.dumps(event.model_dump(mode="json")).encode(),
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            ),
            routing_key=f"raw.bzzoiro.{feed_type}",
        )

    async def publish_domain_event(self, event: DomainEvent) -> None:
        assert self._domain_exchange is not None, "publisher not connected"
        await self._domain_exchange.publish(
            aio_pika.Message(
                body=json.dumps(event.model_dump(mode="json")).encode(),
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            ),
            routing_key=event.event_type,
        )
