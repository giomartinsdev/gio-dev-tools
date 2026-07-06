from __future__ import annotations

import asyncio
from datetime import date, timedelta

from pydantic import BaseModel

from shared.logger import get_logger

from ...infrastructure.bzzoiro_client import BzzoiroClient
from ...infrastructure.rabbitmq_publisher import RabbitMQPublisher
from ...infrastructure.translator import BzzoiroTranslator

logger = get_logger(__name__)


class PollH2HCommand(BaseModel):
    days_behind: int = 1
    days_ahead: int = 3


class PollH2HHandler:
    """Per-event head-to-head record, scoped to the same fixtures date
    window PollFixturesHandler uses. Pure context (doesn't feed edge
    detection) so this can run on a much longer interval than the
    odds/lineups polls — a head-to-head record barely changes between two
    polls of the same fixture window."""

    def __init__(self, client: BzzoiroClient, translator: BzzoiroTranslator, publisher: RabbitMQPublisher):
        self._client = client
        self._translator = translator
        self._publisher = publisher

    async def handle(self, cmd: PollH2HCommand) -> int:
        today = date.today()
        payloads = await asyncio.to_thread(
            self._client.fetch_events,
            today - timedelta(days=cmd.days_behind),
            today + timedelta(days=cmd.days_ahead),
        )
        event_ids = sorted({p.get("id") for p in payloads if p.get("id") is not None}, key=str)

        polled = 0
        for event_ref_id in event_ids:
            try:
                if await self._poll_one_event(event_ref_id):
                    polled += 1
            except Exception as exc:
                logger.warning(f"failed to poll h2h for event {event_ref_id}: {exc}")

        logger.info(f"polled h2h: {polled}/{len(event_ids)} events")
        return polled

    async def _poll_one_event(self, event_ref_id: object) -> bool:
        match_id = self._translator.resolve_match_id(event_ref_id)

        payload = await asyncio.to_thread(self._client.fetch_h2h, event_ref_id)
        if payload is None:
            return False

        await self._publisher.publish_raw(
            "h2h", str(event_ref_id), payload, correlation_id=match_id,
        )
        event = self._translator.translate_h2h(event_ref_id, payload)
        if event is not None:
            await self._publisher.publish_domain_event(event)
            return True
        return False
