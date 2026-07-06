from __future__ import annotations

from shared.logger import get_logger
from shared.events import InsightGenerated

from ..infrastructure.read_model_repository import ReadModelRepository
from .value_bet_detector import ValueBetDetector

logger = get_logger(__name__)


class ProjectInsightHandler:
    """Consumes analysis.events (q.insight.projector). Separate from
    ProjectDomainEventHandler because InsightGenerated is not part of the
    DomainEvent discriminated union — it's routed to its own exchange."""

    def __init__(self, read_models: ReadModelRepository, value_bet_detector: ValueBetDetector):
        self._read_models = read_models
        self._value_bet_detector = value_bet_detector

    async def handle(self, raw_body: bytes) -> None:
        event = InsightGenerated.model_validate_json(raw_body)
        self._read_models.insert_insight(
            insight_id=event.insight_id,
            match_id=event.match_id,
            market=event.market,
            recommendation=event.recommendation,
            confidence=event.confidence,
            rationale=event.rationale,
            model=event.model,
            feature_snapshot=event.feature_snapshot,
            generated_at=event.generated_at,
        )
        try:
            await self._value_bet_detector.evaluate(event.match_id)
        except Exception as exc:
            # A bug in value-bet detection must never poison an otherwise
            # valid insight — insert_insight above already committed in its
            # own transaction (see ProjectDomainEventHandler._evaluate_value_bet
            # for the same guard on the odds/lineup side).
            logger.error(f"value bet evaluation failed for match {event.match_id}: {exc}", exc_info=True)
