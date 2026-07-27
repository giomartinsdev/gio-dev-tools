from __future__ import annotations

import asyncio

import aio_pika

from shared.events import BusPositionCaptured, domain_event_adapter
from shared.logger import get_logger
from shared.rabbitmq_topology import Q_BUS_POSITIONS, declare_topology

from .position_repository import PositionRepository

logger = get_logger(__name__)

RECONNECT_DELAY = 5


class PositionConsumer:
    """Consumes BusPositionCaptured events published by the bus-tracker-poller
    worker, persists them, and fans out the same payload to every SSE
    subscriber — the only coupling between the two services is this queue,
    never a direct HTTP call."""

    def __init__(self, repo: PositionRepository, sse_subs: dict[str, set[asyncio.Queue]]):
        self._repo = repo
        self._sse_subs = sse_subs

    async def run(self, rabbitmq_uri: str) -> None:
        while True:
            try:
                conn = await aio_pika.connect_robust(rabbitmq_uri)
                async with conn:
                    channel = await conn.channel()
                    await channel.set_qos(prefetch_count=20)
                    await declare_topology(channel)
                    queue = await channel.get_queue(Q_BUS_POSITIONS)
                    logger.info(f"consuming {Q_BUS_POSITIONS}")
                    async with queue.iterator() as it:
                        async for message in it:
                            try:
                                await self.project(message.body)
                                await message.ack()
                            except Exception as exc:
                                logger.error(f"poison message on {Q_BUS_POSITIONS}: {exc}", exc_info=True)
                                await message.nack(requeue=False)
            except Exception as exc:
                logger.error(f"{Q_BUS_POSITIONS} consumer error: {exc} — reconnecting in {RECONNECT_DELAY}s")
                await asyncio.sleep(RECONNECT_DELAY)

    async def project(self, raw_body: bytes) -> None:
        event = domain_event_adapter.validate_json(raw_body)
        if not isinstance(event, BusPositionCaptured):
            return

        await asyncio.to_thread(
            self._repo.insert,
            mode=event.mode,
            line_code=event.line_code,
            vehicle_id=event.vehicle_id,
            latitude=event.latitude,
            longitude=event.longitude,
            speed_kmh=event.speed_kmh,
            captured_at=event.captured_at,
            color_hex=event.color_hex,
        )

        payload = {
            "mode": event.mode,
            "line_code": event.line_code,
            "vehicle_id": event.vehicle_id,
            "latitude": event.latitude,
            "longitude": event.longitude,
            "speed_kmh": event.speed_kmh,
            "color_hex": event.color_hex,
            "captured_at": event.captured_at.isoformat(),
        }
        sub_key = f"{event.mode}:{event.line_code}"
        dead = set()
        for sub in list(self._sse_subs.get(sub_key, set())):
            try:
                sub.put_nowait(payload)
            except asyncio.QueueFull:
                dead.add(sub)
        self._sse_subs.get(sub_key, set()).difference_update(dead)
