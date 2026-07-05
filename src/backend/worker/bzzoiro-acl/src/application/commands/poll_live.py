from __future__ import annotations

import asyncio
from uuid import uuid4

from pydantic import BaseModel

from shared.logger import get_logger

from ...infrastructure.bzzoiro_client import BzzoiroClient
from ...infrastructure.rabbitmq_publisher import RabbitMQPublisher
from ...infrastructure.translator import BzzoiroTranslator

logger = get_logger(__name__)


class PollLiveCommand(BaseModel):
    pass


class PollLiveHandler:
    def __init__(self, client: BzzoiroClient, translator: BzzoiroTranslator, publisher: RabbitMQPublisher):
        self._client = client
        self._translator = translator
        self._publisher = publisher

    async def handle(self, cmd: PollLiveCommand) -> int:
        payloads = await asyncio.to_thread(self._client.fetch_live)
        for payload in payloads:
            domain_events = self._translator.translate_event(payload)
            correlation_id = domain_events[0].meta.correlation_id if domain_events else uuid4()
            await self._publisher.publish_raw(
                "live", str(payload.get("id")), payload, correlation_id=correlation_id,
            )
            for event in domain_events:
                await self._publisher.publish_domain_event(event)
        logger.info(f"polled live: {len(payloads)} events")
        return len(payloads)
