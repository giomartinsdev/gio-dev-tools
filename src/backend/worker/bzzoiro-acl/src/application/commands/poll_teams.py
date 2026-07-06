from __future__ import annotations

import asyncio

from pydantic import BaseModel

from shared.logger import get_logger

from ...infrastructure.bzzoiro_client import BzzoiroClient
from ...infrastructure.rabbitmq_publisher import RabbitMQPublisher
from ...infrastructure.translator import BzzoiroTranslator

logger = get_logger(__name__)


class PollTeamsCommand(BaseModel):
    pass


class PollTeamsHandler:
    def __init__(self, client: BzzoiroClient, translator: BzzoiroTranslator, publisher: RabbitMQPublisher):
        self._client = client
        self._translator = translator
        self._publisher = publisher

    async def handle(self, cmd: PollTeamsCommand) -> int:
        payloads = await asyncio.to_thread(self._client.fetch_teams)
        polled_squads = 0
        for i, payload in enumerate(payloads):
            team_ref_id = payload.get("id")
            team_id = self._translator.resolve_team_id(team_ref_id)
            
            # Publish team detail
            await self._publisher.publish_raw("teams", str(team_ref_id), payload, correlation_id=team_id)
            team_event = self._translator.translate_team(payload)
            await self._publisher.publish_domain_event(team_event)

            # Publish team squad (wrapped in try/except to prevent failures from stopping the poll)
            try:
                squad_payload = await asyncio.to_thread(self._client.fetch_squad, team_ref_id)
                players = squad_payload.get("players") if isinstance(squad_payload, dict) else None
                if players:
                    await self._publisher.publish_raw(
                        "team_squad",
                        str(team_ref_id),
                        squad_payload,
                        correlation_id=team_id,
                    )
                    squad_event = self._translator.translate_squad(team_ref_id, players)
                    await self._publisher.publish_domain_event(squad_event)
                    polled_squads += 1
            except Exception as exc:
                logger.warning(f"failed to fetch squad for team {team_ref_id}: {exc}")

            if i > 0 and i % 100 == 0:
                logger.info(f"polled teams progress: {i}/{len(payloads)} teams completed")

        logger.info(f"polled teams complete: {len(payloads)} teams, {polled_squads} squads fetched")
        return len(payloads)
