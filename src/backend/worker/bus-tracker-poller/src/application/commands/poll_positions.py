from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from pydantic import BaseModel

from shared.events import BusPositionCaptured, EventMeta
from shared.logger import get_logger

from ...infrastructure.rabbitmq_publisher import RabbitMQPublisher
from ...infrastructure.rio_gps_client import RioGpsClient, parse_brt_position, parse_sppo_position
from ...infrastructure.tracked_lines_read_repository import TrackedLinesReadRepository

logger = get_logger(__name__)

PRODUCER = "worker.bus-tracker-poller"


class PollPositionsCommand(BaseModel):
    # Matches RJ-SMTR/app-monitoramento-realtime's own SPPO query window
    # (last 5 minutes to now) — the official frontend for this same feed.
    sppo_window_seconds: int = 300


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
        sppo_lines = await asyncio.to_thread(self._tracked_lines.find_active_line_codes, "sppo")
        brt_lines = await asyncio.to_thread(self._tracked_lines.find_active_line_codes, "brt")
        if not sppo_lines and not brt_lines:
            return 0

        colors = await asyncio.to_thread(self._client.fetch_vehicle_colors)

        published = 0
        if sppo_lines:
            published += await self._poll_sppo(cmd, sppo_lines, colors)
        if brt_lines:
            published += await self._poll_brt(brt_lines, colors)
        return published

    async def _poll_sppo(self, cmd: PollPositionsCommand, active_lines: set[str], colors: dict) -> int:
        now = datetime.now(timezone.utc)
        rows = await asyncio.to_thread(
            self._client.fetch_sppo_positions,
            now - timedelta(seconds=cmd.sppo_window_seconds),
            now,
        )
        return await self._publish_matching(rows, active_lines, parse_sppo_position, colors)

    async def _poll_brt(self, active_lines: set[str], colors: dict) -> int:
        rows = await asyncio.to_thread(self._client.fetch_brt_positions)
        return await self._publish_matching(rows, active_lines, parse_brt_position, colors)

    async def _publish_matching(self, rows: list[dict], active_lines: set[str], parse, colors: dict) -> int:
        published = 0
        for row in rows:
            if str(row.get("linha")) not in active_lines:
                continue
            try:
                position = parse(row)
            except ValueError as exc:
                logger.warning(f"skipping malformed row: {exc}")
                continue

            event = BusPositionCaptured(
                meta=EventMeta(
                    occurred_at=datetime.now(timezone.utc),
                    producer=PRODUCER,
                    correlation_id=uuid4(),
                ),
                mode=position["mode"],
                line_code=position["line_code"],
                vehicle_id=position["vehicle_id"],
                latitude=position["latitude"],
                longitude=position["longitude"],
                speed_kmh=position["speed_kmh"],
                captured_at=position["captured_at"],
                color_hex=colors.get(position["vehicle_id"]),
            )
            await self._publisher.publish_domain_event(event)
            published += 1

        return published
