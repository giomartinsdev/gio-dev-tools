from __future__ import annotations

from shared.events import (
    DomainEvent,
    MatchFinished,
    MatchScheduled,
    MatchScoreUpdated,
    MatchStatusChanged,
    OddsSnapshotCaptured,
    TeamUpdated,
    SquadUpdated,
    domain_event_adapter,
)
from shared.logger import get_logger

from ..infrastructure.read_model_repository import ReadModelRepository

logger = get_logger(__name__)


class ProjectDomainEventHandler:
    def __init__(self, read_models: ReadModelRepository):
        self._read_models = read_models

    def handle(self, raw_body: bytes) -> None:
        event: DomainEvent = domain_event_adapter.validate_json(raw_body)
        self._project(event)

    def _project(self, event: DomainEvent) -> None:
        if isinstance(event, MatchScheduled):
            self._read_models.upsert_match_scheduled(
                match_id=event.match_id,
                competition_id=event.competition_id,
                home_team_id=event.home_team_id,
                away_team_id=event.away_team_id,
                kickoff_at=event.kickoff_at,
                venue=event.venue,
            )
        elif isinstance(event, MatchStatusChanged):
            self._read_models.upsert_match_status(
                match_id=event.match_id, status=event.status.value, minute=event.minute,
            )
        elif isinstance(event, MatchScoreUpdated):
            self._read_models.upsert_match_score(
                match_id=event.match_id,
                home_score=event.home_score,
                away_score=event.away_score,
                minute=event.minute,
            )
        elif isinstance(event, MatchFinished):
            self._read_models.upsert_match_finished(
                match_id=event.match_id,
                home_score=event.home_score,
                away_score=event.away_score,
                statistics=event.statistics,
            )
        elif isinstance(event, OddsSnapshotCaptured):
            self._read_models.insert_odds_snapshot(
                event_id=event.meta.event_id,
                match_id=event.match_id,
                bookmaker=event.bookmaker,
                market=event.market,
                selections=[s.model_dump(mode="json") for s in event.selections],
                captured_at=event.captured_at,
            )
        elif isinstance(event, TeamUpdated):
            self._read_models.upsert_team(
                team_id=event.team_id,
                name=event.name,
                short_name=event.short_name,
                country=event.country,
                venue_id=event.venue_id,
            )
        elif isinstance(event, SquadUpdated):
            self._read_models.upsert_squad(
                team_id=event.team_id,
                members=event.members,
            )
        else:
            logger.warning(f"unhandled domain event type: {type(event).__name__}")
