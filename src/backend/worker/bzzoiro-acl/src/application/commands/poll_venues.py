from __future__ import annotations

import asyncio
from datetime import date, timedelta

from pydantic import BaseModel

from shared.logger import get_logger

from ...infrastructure.bzzoiro_client import BzzoiroClient
from ...infrastructure.rabbitmq_publisher import RabbitMQPublisher
from ...infrastructure.translator import BzzoiroTranslator

logger = get_logger(__name__)


class PollVenuesCommand(BaseModel):
    days_behind: int = 1
    days_ahead: int = 3


class PollVenuesHandler:
    """Per-venue detail, scoped to venues actually in play in the same
    fixtures date window PollFixturesHandler uses (a `venue_id` per event,
    confirmed live on the real EventDetailV2Schema payload) rather than a
    full crawl of bzzoiro's entire venue catalogue. Exists so
    `MatchScheduled.venue` can eventually carry a real name — the events
    feed only ever has `venue_id`, never a name string. Pure context,
    doesn't feed edge detection, so a slow/failed venue doesn't block the
    rest."""

    def __init__(self, client: BzzoiroClient, translator: BzzoiroTranslator, publisher: RabbitMQPublisher):
        self._client = client
        self._translator = translator
        self._publisher = publisher

    async def handle(self, cmd: PollVenuesCommand) -> int:
        today = date.today()
        payloads = await asyncio.to_thread(
            self._client.fetch_events,
            today - timedelta(days=cmd.days_behind),
            today + timedelta(days=cmd.days_ahead),
        )
        venue_ids = sorted(
            {p.get("venue_id") for p in payloads if p.get("venue_id") is not None}, key=str,
        )

        polled = 0
        for venue_ref_id in venue_ids:
            try:
                if await self._poll_one_venue(venue_ref_id):
                    polled += 1
            except Exception as exc:
                logger.warning(f"failed to poll venue {venue_ref_id}: {exc}")

        logger.info(f"polled venues: {polled}/{len(venue_ids)}")
        return polled

    async def _poll_one_venue(self, venue_ref_id: object) -> bool:
        venue_id = self._translator.resolve_venue_id(venue_ref_id)

        payload = await asyncio.to_thread(self._client.fetch_venue, venue_ref_id)
        if payload is None:
            return False

        await self._publisher.publish_raw(
            "venue", str(venue_ref_id), payload, correlation_id=venue_id,
        )
        event = self._translator.translate_venue(venue_ref_id, payload)
        if event is not None:
            await self._publisher.publish_domain_event(event)
            return True
        return False
