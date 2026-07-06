from __future__ import annotations

import asyncio
from datetime import date, timedelta

from pydantic import BaseModel

from shared.logger import get_logger

from ...infrastructure.bzzoiro_client import BzzoiroClient
from ...infrastructure.rabbitmq_publisher import RabbitMQPublisher
from ...infrastructure.translator import BzzoiroTranslator

logger = get_logger(__name__)

_NOT_YET_KICKED_OFF = {"notstarted", "postponed", "cancelled"}


class PollPlayerStatsCommand(BaseModel):
    days_behind: int = 1
    days_ahead: int = 3


class PollPlayerStatsHandler:
    """Per-player stat lines, scoped to fixtures in the same date window
    PollFixturesHandler uses that have actually kicked off — bzzoiro only
    populates this endpoint once a match is live/finished, so fixtures
    still `notstarted`/`postponed`/`cancelled` are skipped without even
    trying. Pure review context, doesn't feed edge detection."""

    def __init__(self, client: BzzoiroClient, translator: BzzoiroTranslator, publisher: RabbitMQPublisher):
        self._client = client
        self._translator = translator
        self._publisher = publisher

    async def handle(self, cmd: PollPlayerStatsCommand) -> int:
        today = date.today()
        payloads = await asyncio.to_thread(
            self._client.fetch_events,
            today - timedelta(days=cmd.days_behind),
            today + timedelta(days=cmd.days_ahead),
        )
        event_ids = sorted(
            {
                p.get("id") for p in payloads
                if p.get("id") is not None and str(p.get("status")) not in _NOT_YET_KICKED_OFF
            },
            key=str,
        )

        polled = 0
        for event_ref_id in event_ids:
            try:
                if await self._poll_one_event(event_ref_id):
                    polled += 1
            except Exception as exc:
                logger.warning(f"failed to poll player stats for event {event_ref_id}: {exc}")

        logger.info(f"polled player stats: {polled}/{len(event_ids)} events")
        return polled

    async def _poll_one_event(self, event_ref_id: object) -> bool:
        match_id = self._translator.resolve_match_id(event_ref_id)

        payload = await asyncio.to_thread(self._client.fetch_player_stats, event_ref_id)
        if payload is None:
            return False

        await self._publisher.publish_raw(
            "player_stats", str(event_ref_id), payload, correlation_id=match_id,
        )
        event = self._translator.translate_player_stats(event_ref_id, payload)
        if event is not None:
            await self._publisher.publish_domain_event(event)
            return True
        return False
