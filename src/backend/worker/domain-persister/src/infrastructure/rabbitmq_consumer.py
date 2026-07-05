from __future__ import annotations

import asyncio

import aio_pika

from shared.events import RawFeedReceived
from shared.logger import get_logger
from shared.rabbitmq_topology import Q_ARCHIVE_RAW, Q_PERSISTER, declare_topology

from ..application.project_domain_event import ProjectDomainEventHandler
from .event_store_repository import EventStoreRepository

logger = get_logger(__name__)

RECONNECT_DELAY = 5


async def _consume_archive_raw(uri: str, event_store: EventStoreRepository) -> None:
    while True:
        try:
            conn = await aio_pika.connect_robust(uri)
            async with conn:
                channel = await conn.channel()
                await channel.set_qos(prefetch_count=20)
                await declare_topology(channel)
                queue = await channel.get_queue(Q_ARCHIVE_RAW)
                logger.info(f"consuming {Q_ARCHIVE_RAW}")
                async with queue.iterator() as it:
                    async for message in it:
                        try:
                            envelope = RawFeedReceived.model_validate_json(message.body)
                            event_store.append(
                                event_id=str(envelope.meta.event_id),
                                event_type=envelope.event_type,
                                occurred_at=envelope.meta.occurred_at,
                                payload=envelope.model_dump(mode="json"),
                            )
                            await message.ack()
                        except Exception as exc:
                            logger.error(f"poison message on {Q_ARCHIVE_RAW}: {exc}", exc_info=True)
                            await message.nack(requeue=False)
        except Exception as exc:
            logger.error(f"{Q_ARCHIVE_RAW} consumer error: {exc} — reconnecting in {RECONNECT_DELAY}s")
            await asyncio.sleep(RECONNECT_DELAY)


async def _consume_persister(uri: str, projector: ProjectDomainEventHandler) -> None:
    while True:
        try:
            conn = await aio_pika.connect_robust(uri)
            async with conn:
                channel = await conn.channel()
                await channel.set_qos(prefetch_count=20)
                await declare_topology(channel)
                queue = await channel.get_queue(Q_PERSISTER)
                logger.info(f"consuming {Q_PERSISTER}")
                async with queue.iterator() as it:
                    async for message in it:
                        try:
                            projector.handle(message.body)
                            await message.ack()
                        except Exception as exc:
                            logger.error(f"poison message on {Q_PERSISTER}: {exc}", exc_info=True)
                            await message.nack(requeue=False)
        except Exception as exc:
            logger.error(f"{Q_PERSISTER} consumer error: {exc} — reconnecting in {RECONNECT_DELAY}s")
            await asyncio.sleep(RECONNECT_DELAY)


async def run_consumers(
    uri: str, event_store: EventStoreRepository, projector: ProjectDomainEventHandler,
) -> None:
    await asyncio.gather(
        _consume_archive_raw(uri, event_store),
        _consume_persister(uri, projector),
    )
