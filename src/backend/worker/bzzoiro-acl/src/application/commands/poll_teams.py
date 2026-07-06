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
        for payload in payloads:
            team_id = self._translator.resolve_team_id(payload.get("id"))
            await self._publisher.publish_raw("teams", str(payload.get("id")), payload, correlation_id=team_id)
            event = self._translator.translate_team(payload)
            await self._publisher.publish_domain_event(event)
        logger.info(f"polled teams: {len(payloads)} events")
        return len(payloads)
