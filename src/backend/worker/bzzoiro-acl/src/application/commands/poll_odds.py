from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from shared.logger import get_logger

from ...infrastructure.bzzoiro_client import BzzoiroClient
from ...infrastructure.rabbitmq_publisher import RabbitMQPublisher
from ...infrastructure.translator import BzzoiroTranslator

logger = get_logger(__name__)


class PollOddsCommand(BaseModel):
    updated_after: Optional[datetime] = None


class PollOddsHandler:
    def __init__(self, client: BzzoiroClient, translator: BzzoiroTranslator, publisher: RabbitMQPublisher):
        self._client = client
        self._translator = translator
        self._publisher = publisher

    async def handle(self, cmd: PollOddsCommand) -> int:
        items = await asyncio.to_thread(self._client.fetch_odds, cmd.updated_after)
        for item in items:
            match_id = self._translator.resolve_match_id(item.get("event_id"))
            await self._publisher.publish_raw("odds", str(item.get("id")), item, correlation_id=match_id)
        for event in self._translator.translate_odds_items(items):
            await self._publisher.publish_domain_event(event)
        logger.info(f"polled odds: {len(items)} rows")
        return len(items)
