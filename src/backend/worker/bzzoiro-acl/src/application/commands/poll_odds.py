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
        """Fetch odds page-by-page (offset-by-offset) and publish events immediately.

        Returns (total_count, last_updated_at) where last_updated_at is the most
        recent updated_at seen in any of the processed pages.
        """
        offset = 0
        limit = 200
        total_count = 0
        last_updated_at: Optional[datetime] = None

        while True:
            # Fetch one page from the client
            items, has_next = await asyncio.to_thread(
                self._client.fetch_odds_page, offset, limit, cmd.updated_after
            )
            if not items:
                break

            # Publish raw odds for this page immediately
            for item in items:
                match_id = self._translator.resolve_match_id(item.get("event_id"))
                await self._publisher.publish_raw("odds", str(item.get("id")), item, correlation_id=match_id)

            # Translate and publish canonical domain events for this page immediately
            for event in self._translator.translate_odds_items(items):
                await self._publisher.publish_domain_event(event)

            # Track total count and find the latest updated_at across all items
            total_count += len(items)
            for item in items:
                if item.get("updated_at"):
                    try:
                        dt = datetime.fromisoformat(item["updated_at"].replace("Z", "+00:00"))
                        if last_updated_at is None or dt > last_updated_at:
                            last_updated_at = dt
                    except (ValueError, TypeError):
                        pass

            logger.info(f"polled odds batch: offset={offset}, items={len(items)}, total={total_count}")

            if not has_next or len(items) < limit:
                break
            offset += limit

        logger.info(f"polled odds complete: {total_count} rows, last_updated_at={last_updated_at}")
        return total_count, last_updated_at


