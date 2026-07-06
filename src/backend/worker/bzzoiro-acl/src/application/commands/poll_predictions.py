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
        polled = 0
        for payload in payloads:
            try:
                await self._poll_one_prediction(payload)
                polled += 1
            except Exception as exc:
                logger.warning(f"failed to process prediction {payload.get('id')}: {exc}")
        logger.info(f"polled predictions: {polled}/{len(payloads)} rows")
        return polled

    async def _poll_one_prediction(self, payload: dict) -> None:
        event = payload["event"]
        match_id = self._translator.resolve_match_id(event["id"])
        await self._publisher.publish_raw("predictions", str(payload.get("id")), payload, correlation_id=match_id)

        # Predictions cover a far wider set of "upcoming" matches than
        # PollFixturesHandler's 3-day window (confirmed live: 293 vs a
        # handful) — without publishing these too, an insight can point at
        # a match_id with no row in matches/teams yet, showing up as blank
        # team names anywhere that joins on them.
        for context_event in self._translator.translate_prediction_context(event):
            await self._publisher.publish_domain_event(context_event)

        insight = self._translator.translate_prediction(payload)
        await self._publisher.publish_insight(insight)
