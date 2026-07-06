from __future__ import annotations

from shared.events import InsightGenerated

from ..infrastructure.read_model_repository import ReadModelRepository
from .value_bet_detector import ValueBetDetector


class ProjectInsightHandler:
    """Consumes analysis.events (q.insight.projector). Separate from
    ProjectDomainEventHandler because InsightGenerated is not part of the
    DomainEvent discriminated union — it's routed to its own exchange."""

    def __init__(self, read_models: ReadModelRepository, value_bet_detector: ValueBetDetector):
        self._read_models = read_models
        self._value_bet_detector = value_bet_detector

    def handle(self, raw_body: bytes) -> None:
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
        self._value_bet_detector.evaluate(event.match_id)
