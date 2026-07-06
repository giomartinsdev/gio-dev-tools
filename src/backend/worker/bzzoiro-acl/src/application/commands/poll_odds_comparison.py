from __future__ import annotations

import asyncio
from datetime import date, timedelta

from pydantic import BaseModel

from shared.logger import get_logger

from ...infrastructure.bzzoiro_client import BzzoiroClient
from ...infrastructure.rabbitmq_publisher import RabbitMQPublisher
from ...infrastructure.translator import BzzoiroTranslator

logger = get_logger(__name__)


class PollOddsComparisonCommand(BaseModel):
    days_behind: int = 1
    days_ahead: int = 3


class PollOddsComparisonHandler:
    """Per-event odds comparison + Polymarket, scoped to the same fixtures
    date window PollFixturesHandler already uses (not the global
    `/api/v2/odds/` firehose, and not the broken `/api/v2/events/live/`
    endpoint — its response envelope uses an `events` key instead of
    `results`, so it never returns anything through `_paginate_v2`).
    """

    def __init__(self, client: BzzoiroClient, translator: BzzoiroTranslator, publisher: RabbitMQPublisher):
        self._client = client
        self._translator = translator
        self._publisher = publisher

    async def handle(self, cmd: PollOddsComparisonCommand) -> int:
        today = date.today()
        payloads = await asyncio.to_thread(
            self._client.fetch_events,
            today - timedelta(days=cmd.days_behind),
            today + timedelta(days=cmd.days_ahead),
        )
        event_ids = sorted({p.get("id") for p in payloads if p.get("id") is not None}, key=str)

        with_odds = 0
        for event_ref_id in event_ids:
            match_id = self._translator.resolve_match_id(event_ref_id)

            comparison = await asyncio.to_thread(self._client.fetch_odds_comparison, event_ref_id)
            if comparison is not None:
                await self._publisher.publish_raw(
                    "odds_comparison", str(event_ref_id), comparison, correlation_id=match_id,
                )
                await self._publisher.publish_domain_event(
                    self._translator.translate_odds_comparison(comparison)
                )
                with_odds += 1

            polymarket = await asyncio.to_thread(self._client.fetch_polymarket, event_ref_id)
            if polymarket is not None:
                await self._publisher.publish_raw(
                    "polymarket", str(event_ref_id), polymarket, correlation_id=match_id,
                )
                poly_event = self._translator.translate_polymarket(event_ref_id, polymarket)
                if poly_event is not None:
                    await self._publisher.publish_domain_event(poly_event)

        logger.info(f"polled odds comparison: {with_odds}/{len(event_ids)} events had odds")
        return with_odds
