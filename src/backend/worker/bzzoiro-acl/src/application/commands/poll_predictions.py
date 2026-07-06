from __future__ import annotations

import asyncio

from pydantic import BaseModel

from shared.logger import get_logger

from ...infrastructure.bzzoiro_client import BzzoiroClient
from ...infrastructure.rabbitmq_publisher import RabbitMQPublisher
from ...infrastructure.translator import BzzoiroTranslator

logger = get_logger(__name__)


class PollPredictionsCommand(BaseModel):
    status: str = "upcoming"


class PollPredictionsHandler:
    def __init__(self, client: BzzoiroClient, translator: BzzoiroTranslator, publisher: RabbitMQPublisher):
        self._client = client
        self._translator = translator
        self._publisher = publisher

    async def handle(self, cmd: PollPredictionsCommand) -> int:
        payloads = await asyncio.to_thread(self._client.fetch_predictions, cmd.status)
        for payload in payloads:
            match_id = self._translator.resolve_match_id(payload["event"]["id"])
            await self._publisher.publish_raw("predictions", str(payload.get("id")), payload, correlation_id=match_id)
            insight = self._translator.translate_prediction(payload)
            await self._publisher.publish_insight(insight)
        logger.info(f"polled predictions: {len(payloads)} rows")
        return len(payloads)
