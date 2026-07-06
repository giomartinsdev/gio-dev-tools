from __future__ import annotations

import asyncio
from datetime import date, timedelta

from pydantic import BaseModel

from shared.logger import get_logger

from ...infrastructure.bzzoiro_client import BzzoiroClient
from ...infrastructure.rabbitmq_publisher import RabbitMQPublisher
from ...infrastructure.translator import BzzoiroTranslator

logger = get_logger(__name__)


class PollStandingsCommand(BaseModel):
    days_behind: int = 1
    days_ahead: int = 3


class PollStandingsHandler:
    """Per-league standings, scoped to leagues actually active in the same
    fixtures date window PollFixturesHandler uses (a `league_id` per event,
    confirmed live on the real EventDetailV2Schema payload — flat, not the
    nested `league.id` some other translation code assumes), rather than a
    full crawl of bzzoiro's entire league catalogue. Pure context, doesn't
    feed edge detection, so a slow/failed league doesn't block the rest."""

    def __init__(self, client: BzzoiroClient, translator: BzzoiroTranslator, publisher: RabbitMQPublisher):
        self._client = client
        self._translator = translator
        self._publisher = publisher

    async def handle(self, cmd: PollStandingsCommand) -> int:
        today = date.today()
        payloads = await asyncio.to_thread(
            self._client.fetch_events,
            today - timedelta(days=cmd.days_behind),
            today + timedelta(days=cmd.days_ahead),
        )
        league_ids = sorted(
            {p.get("league_id") for p in payloads if p.get("league_id") is not None}, key=str,
        )

        polled = 0
        for league_ref_id in league_ids:
            try:
                if await self._poll_one_league(league_ref_id):
                    polled += 1
            except Exception as exc:
                logger.warning(f"failed to poll standings for league {league_ref_id}: {exc}")

        logger.info(f"polled standings: {polled}/{len(league_ids)} leagues")
        return polled

    async def _poll_one_league(self, league_ref_id: object) -> bool:
        competition_id = self._translator.resolve_competition_id(league_ref_id)

        payload = await asyncio.to_thread(self._client.fetch_standings, league_ref_id)
        if payload is None:
            return False

        await self._publisher.publish_raw(
            "standings", str(league_ref_id), payload, correlation_id=competition_id,
        )
        event = self._translator.translate_standings(league_ref_id, payload)
        if event is not None:
            await self._publisher.publish_domain_event(event)
            return True
        return False
