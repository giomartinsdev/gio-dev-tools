from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from shared.logger import get_logger

from ...infrastructure.bzzoiro_client import BzzoiroClient
from ...infrastructure.rabbitmq_publisher import RabbitMQPublisher
from ...infrastructure.sync_checkpoint_repository import SyncCheckpointRepository
from ...infrastructure.translator import BzzoiroTranslator

logger = get_logger(__name__)

FEED_TYPE = "odds"


class PollOddsCommand(BaseModel):
    force: bool = False


def _parse_updated_at(value: object) -> Optional[datetime]:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


class PollOddsHandler:
    """Fetches odds page-by-page, publishing each page immediately, and
    tracks its own `updated_after` checkpoint (bzzoiro-acl's own table, not
    domain-persister's `odds_snapshots`) so a restart resumes from where the
    last successful poll left off instead of re-pulling the full history.
    Pass `PollOddsCommand(force=True)` to ignore the checkpoint and do a
    full resync.
    """

    def __init__(
        self,
        client: BzzoiroClient,
        translator: BzzoiroTranslator,
        publisher: RabbitMQPublisher,
        checkpoints: SyncCheckpointRepository,
    ):
        self._client = client
        self._translator = translator
        self._publisher = publisher
        self._checkpoints = checkpoints

    async def handle(self, cmd: PollOddsCommand) -> int:
        updated_after = await self._load_checkpoint(cmd.force)

        offset = 0
        limit = 200
        total = 0
        latest_seen = updated_after

        while True:
            items, has_next = await asyncio.to_thread(
                self._client.fetch_odds_page, offset, limit, updated_after,
            )
            if not items:
                break

            for item in items:
                match_id = self._translator.resolve_match_id(item.get("event_id"))
                await self._publisher.publish_raw("odds", str(item.get("id")), item, correlation_id=match_id)

            for event in self._translator.translate_odds_items(items):
                await self._publisher.publish_domain_event(event)

            total += len(items)
            for item in items:
                seen = _parse_updated_at(item.get("updated_at"))
                if seen is not None and (latest_seen is None or seen > latest_seen):
                    latest_seen = seen

            logger.info(f"odds poll batch: offset={offset}, items={len(items)}, total={total}")

            if not has_next:
                break
            offset += limit

        if latest_seen is not None:
            await asyncio.to_thread(self._checkpoints.set_cursor, FEED_TYPE, latest_seen.isoformat())

        logger.info(f"polled odds: {total} rows (checkpoint={latest_seen})")
        return total

    async def _load_checkpoint(self, force: bool) -> Optional[datetime]:
        if force:
            return None
        cursor = await asyncio.to_thread(self._checkpoints.get_cursor, FEED_TYPE)
        return _parse_updated_at(cursor)
