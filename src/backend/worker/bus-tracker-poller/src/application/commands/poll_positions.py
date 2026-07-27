from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from pydantic import BaseModel

from shared.events import BusPositionCaptured, EventMeta
from shared.logger import get_logger

from ...infrastructure.rabbitmq_publisher import RabbitMQPublisher
from ...infrastructure.rio_gps_client import RioGpsClient, parse_position
from ...infrastructure.tracked_lines_read_repository import TrackedLinesReadRepository

logger = get_logger(__name__)

PRODUCER = "worker.bus-tracker-poller"


class PollPositionsCommand(BaseModel):
    window_seconds: int = 120


class PollPositionsHandler:
    def __init__(
        self,
        client: RioGpsClient,
        tracked_lines: TrackedLinesReadRepository,
        publisher: RabbitMQPublisher,
    ):
        self._client = client
        self._tracked_lines = tracked_lines
        self._publisher = publisher

    async def handle(self, cmd: PollPositionsCommand) -> int:
        active_lines = await asyncio.to_thread(self._tracked_lines.find_active_line_codes)
        if not active_lines:
            return 0

        now = datetime.now(timezone.utc)
        rows = await asyncio.to_thread(
            self._client.fetch_positions, now - timedelta(seconds=cmd.window_seconds), now,
        )

        published = 0
        for row in rows:
            if str(row.get("linha")) not in active_lines:
                continue
            try:
                position = parse_position(row)
            except ValueError as exc:
                logger.warning(f"skipping malformed SPPO row: {exc}")
                continue

            event = BusPositionCaptured(
                meta=EventMeta(
                    occurred_at=datetime.now(timezone.utc),
                    producer=PRODUCER,
                    correlation_id=uuid4(),
                ),
                line_code=position["line_code"],
                vehicle_id=position["vehicle_id"],
                latitude=position["latitude"],
                longitude=position["longitude"],
                speed_kmh=position["speed_kmh"],
                captured_at=position["captured_at"],
            )
            await self._publisher.publish_domain_event(event)
            published += 1

        return published
