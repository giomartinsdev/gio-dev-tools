from __future__ import annotations

import asyncio

from pydantic import BaseModel

from shared.logger import get_logger

from ...infrastructure.bzzoiro_client import BzzoiroClient
from ...infrastructure.rabbitmq_publisher import RabbitMQPublisher
from ...infrastructure.translator import BzzoiroTranslator

logger = get_logger(__name__)


class PollOddsBestCommand(BaseModel):
    pass


class PollOddsBestHandler:
    """GET /api/v2/odds/best/ — a single paginated call covering the best
    1x2 price for every event bzzoiro tracks odds for, much cheaper than
    PollOddsComparisonHandler's one-call-per-event approach. Only ever
    updates the "1x2" key of each match's odds_comparisons row (a partial
    merge on the persister side, not a replace), so this can run far more
    often than the full comparison poll without risking clobbering
    over_under/btts data that poll captured."""

    def __init__(self, client: BzzoiroClient, translator: BzzoiroTranslator, publisher: RabbitMQPublisher):
        self._client = client
        self._translator = translator
        self._publisher = publisher

    async def handle(self, cmd: PollOddsBestCommand) -> int:
        rows = await asyncio.to_thread(self._client.fetch_odds_best)

        published = 0
        for row in rows:
            try:
                if await self._publish_one_row(row):
                    published += 1
            except Exception as exc:
                logger.warning(f"failed to publish odds-best row {row.get('event_id')}: {exc}")

        logger.info(f"polled odds best: {published}/{len(rows)} rows published")
        return published

    async def _publish_one_row(self, row: dict) -> bool:
        event = self._translator.translate_odds_best(row)
        if event is None:
            return False

        event_ref_id = row.get("event_id")
        await self._publisher.publish_raw(
            "odds_best", str(event_ref_id), row, correlation_id=event.match_id,
        )
        await self._publisher.publish_domain_event(event)
        return True
