from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from pydantic import BaseModel

from shared.logger import get_logger

from ...infrastructure.bzzoiro_client import BzzoiroClient
from ...infrastructure.rabbitmq_publisher import RabbitMQPublisher
from ...infrastructure.sync_checkpoint_repository import SyncCheckpointRepository
from ...infrastructure.translator import BzzoiroTranslator

logger = get_logger(__name__)

FEED_TYPE = "teams"


class PollTeamsCommand(BaseModel):
    force: bool = False


class PollTeamsHandler:
    """Teams/squads barely ever change, so a full crawl (one request per
    team just for its squad) is only worth repeating after `min_resync_seconds`
    has actually passed — not on every process restart. The last full-sync
    timestamp is bzzoiro-acl's own checkpoint, not read by anyone else.
    Pass `PollTeamsCommand(force=True)` to bypass the skip and resync now.
    """

    def __init__(
        self,
        client: BzzoiroClient,
        translator: BzzoiroTranslator,
        publisher: RabbitMQPublisher,
        checkpoints: SyncCheckpointRepository,
        min_resync_seconds: int = 86400,
    ):
        self._client = client
        self._translator = translator
        self._publisher = publisher
        self._checkpoints = checkpoints
        self._min_resync_seconds = min_resync_seconds

    async def handle(self, cmd: PollTeamsCommand) -> int:
        if not cmd.force:
            skip, elapsed = await self._should_skip()
            if skip:
                logger.info(
                    f"teams poll skipped: last full sync {elapsed:.0f}s ago "
                    f"(< {self._min_resync_seconds}s); pass force=True to override"
                )
                return 0

        payloads = await asyncio.to_thread(self._client.fetch_teams)
        polled_squads = 0
        for i, payload in enumerate(payloads):
            team_ref_id = payload.get("id")
            team_id = self._translator.resolve_team_id(team_ref_id)

            await self._publisher.publish_raw("teams", str(team_ref_id), payload, correlation_id=team_id)
            team_event = self._translator.translate_team(payload)
            await self._publisher.publish_domain_event(team_event)

            try:
                squad_payload = await asyncio.to_thread(self._client.fetch_squad, team_ref_id)
                players = squad_payload.get("players") if isinstance(squad_payload, dict) else None
                if players:
                    await self._publisher.publish_raw(
                        "team_squad", str(team_ref_id), squad_payload, correlation_id=team_id,
                    )
                    squad_event = self._translator.translate_squad(team_ref_id, players)
                    await self._publisher.publish_domain_event(squad_event)
                    polled_squads += 1
            except Exception as exc:
                logger.warning(f"failed to fetch squad for team {team_ref_id}: {exc}")

            if i > 0 and i % 100 == 0:
                logger.info(f"polled teams progress: {i}/{len(payloads)} teams completed")

        await asyncio.to_thread(
            self._checkpoints.set_cursor, FEED_TYPE, datetime.now(timezone.utc).isoformat(),
        )
        logger.info(f"polled teams complete: {len(payloads)} teams, {polled_squads} squads fetched")
        return len(payloads)

    async def _should_skip(self) -> tuple[bool, float]:
        cursor = await asyncio.to_thread(self._checkpoints.get_cursor, FEED_TYPE)
        if not cursor:
            return False, 0.0
        try:
            last_sync = datetime.fromisoformat(cursor.replace("Z", "+00:00"))
        except ValueError:
            return False, 0.0
        elapsed = (datetime.now(timezone.utc) - last_sync).total_seconds()
        return elapsed < self._min_resync_seconds, elapsed
