from __future__ import annotations

import asyncio
from datetime import date, timedelta

from pydantic import BaseModel

from shared.logger import get_logger

from ...infrastructure.bzzoiro_client import BzzoiroClient
from ...infrastructure.rabbitmq_publisher import RabbitMQPublisher
from ...infrastructure.translator import BzzoiroTranslator

logger = get_logger(__name__)


class PollRefereesCommand(BaseModel):
    days_behind: int = 1
    days_ahead: int = 3


class PollRefereesHandler:
    """Per-referee detail, scoped to referees assigned in the same fixtures
    date window PollFixturesHandler uses. Confirmed live: `referee_id` is
    often null for not-yet-assigned fixtures, so this naturally skips those
    until an assignment lands. Pure context (card/foul tendency), doesn't
    feed edge detection, so a slow/failed referee doesn't block the rest."""

    def __init__(self, client: BzzoiroClient, translator: BzzoiroTranslator, publisher: RabbitMQPublisher):
        self._client = client
        self._translator = translator
        self._publisher = publisher

    async def handle(self, cmd: PollRefereesCommand) -> int:
        today = date.today()
        payloads = await asyncio.to_thread(
            self._client.fetch_events,
            today - timedelta(days=cmd.days_behind),
            today + timedelta(days=cmd.days_ahead),
        )
        referee_ids = sorted(
            {p.get("referee_id") for p in payloads if p.get("referee_id") is not None}, key=str,
        )

        polled = 0
        for referee_ref_id in referee_ids:
            try:
                if await self._poll_one_referee(referee_ref_id):
                    polled += 1
            except Exception as exc:
                logger.warning(f"failed to poll referee {referee_ref_id}: {exc}")

        logger.info(f"polled referees: {polled}/{len(referee_ids)}")
        return polled

    async def _poll_one_referee(self, referee_ref_id: object) -> bool:
        referee_id = self._translator.resolve_referee_id(referee_ref_id)

        payload = await asyncio.to_thread(self._client.fetch_referee, referee_ref_id)
        if payload is None:
            return False

        await self._publisher.publish_raw(
            "referee", str(referee_ref_id), payload, correlation_id=referee_id,
        )
        event = self._translator.translate_referee(referee_ref_id, payload)
        if event is not None:
            await self._publisher.publish_domain_event(event)
            return True
        return False
