from __future__ import annotations

import asyncio
from datetime import date, timedelta
from uuid import uuid4

from pydantic import BaseModel

from shared.logger import get_logger

from ...infrastructure.bzzoiro_client import BzzoiroClient
from ...infrastructure.rabbitmq_publisher import RabbitMQPublisher
from ...infrastructure.translator import BzzoiroTranslator

logger = get_logger(__name__)


class PollFixturesCommand(BaseModel):
    days_behind: int = 1
    days_ahead: int = 3


class PollFixturesHandler:
    def __init__(self, client: BzzoiroClient, translator: BzzoiroTranslator, publisher: RabbitMQPublisher):
        self._client = client
        self._translator = translator
        self._publisher = publisher

    async def handle(self, cmd: PollFixturesCommand) -> int:
        today = date.today()
        payloads = await asyncio.to_thread(
            self._client.fetch_events,
            today - timedelta(days=cmd.days_behind),
            today + timedelta(days=cmd.days_ahead),
        )
        for payload in payloads:
            domain_events = self._translator.translate_event(payload)
            correlation_id = domain_events[0].meta.correlation_id if domain_events else uuid4()
            await self._publisher.publish_raw(
                "fixtures", str(payload.get("id")), payload, correlation_id=correlation_id,
            )
            for event in domain_events:
                await self._publisher.publish_domain_event(event)
        logger.info(f"polled fixtures: {len(payloads)} events")
        return len(payloads)
