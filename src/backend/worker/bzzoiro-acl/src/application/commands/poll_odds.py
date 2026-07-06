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

    async def handle(self, cmd: PollOddsCommand) -> tuple[int, Optional[datetime]]:
        """Fetch odds and publish events.

        Returns (count, last_updated_at) where last_updated_at is the most recent
        updated_at seen in this batch — the caller should pass it as updated_after
        on the next cycle to avoid re-fetching the entire dataset.
        """
        items = await asyncio.to_thread(self._client.fetch_odds, cmd.updated_after)
        for item in items:
            match_id = self._translator.resolve_match_id(item.get("event_id"))
            await self._publisher.publish_raw("odds", str(item.get("id")), item, correlation_id=match_id)
        for event in self._translator.translate_odds_items(items):
            await self._publisher.publish_domain_event(event)

        last_updated_at: Optional[datetime] = None
        if items:
            raw = max(item["updated_at"] for item in items if item.get("updated_at"))
            last_updated_at = datetime.fromisoformat(raw.replace("Z", "+00:00"))

        logger.info(f"polled odds: {len(items)} rows, last_updated_at={last_updated_at}")
        return len(items), last_updated_at

