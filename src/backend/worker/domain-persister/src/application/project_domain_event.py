from __future__ import annotations

from shared.events import (
    DomainEvent,
    H2HCaptured,
    IncidentsCaptured,
    LineupsCaptured,
    MatchFinished,
    MatchScheduled,
    MatchScoreUpdated,
    MatchStatusChanged,
    OddsBestCaptured,
    OddsComparisonCaptured,
    OddsSnapshotCaptured,
    PlayerStatsCaptured,
    PolymarketSnapshotCaptured,
    RefereeCaptured,
    StandingsCaptured,
    TeamUpdated,
    SquadUpdated,
    VenueCaptured,
    domain_event_adapter,
)
from shared.logger import get_logger

from ..infrastructure.read_model_repository import ReadModelRepository
from .value_bet_detector import ValueBetDetector
from .value_bet_outcome_resolver import ValueBetOutcomeResolver

logger = get_logger(__name__)


class ProjectDomainEventHandler:
    def __init__(
        self,
        read_models: ReadModelRepository,
        value_bet_detector: ValueBetDetector,
        value_bet_outcome_resolver: ValueBetOutcomeResolver,
    ):
        self._read_models = read_models
        self._value_bet_detector = value_bet_detector
        self._value_bet_outcome_resolver = value_bet_outcome_resolver

    async def handle(self, raw_body: bytes) -> None:
        event: DomainEvent = domain_event_adapter.validate_json(raw_body)
        await self._project(event)

    async def _project(self, event: DomainEvent) -> None:
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
            self._resolve_value_bet_outcomes(event.match_id, event.home_score, event.away_score)
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
        elif isinstance(event, OddsComparisonCaptured):
            self._read_models.upsert_odds_comparison(
                match_id=event.match_id,
                bookmakers_count=event.bookmakers_count,
                total_odds=event.total_odds,
                markets=event.markets,
                captured_at=event.captured_at,
            )
            await self._evaluate_value_bet(event.match_id)
        elif isinstance(event, PolymarketSnapshotCaptured):
            self._read_models.upsert_polymarket_snapshot(
                match_id=event.match_id,
                markets=event.markets,
                captured_at=event.captured_at,
            )
        elif isinstance(event, OddsBestCaptured):
            self._read_models.merge_odds_comparison_markets(
                match_id=event.match_id,
                markets_patch=event.markets,
                captured_at=event.captured_at,
            )
            await self._evaluate_value_bet(event.match_id)
        elif isinstance(event, LineupsCaptured):
            self._read_models.upsert_lineups(
                match_id=event.match_id,
                lineup_status=event.lineup_status,
                lineups=event.lineups,
                captured_at=event.captured_at,
            )
            await self._evaluate_value_bet(event.match_id)
        elif isinstance(event, H2HCaptured):
            self._read_models.upsert_h2h(
                match_id=event.match_id, h2h=event.h2h, captured_at=event.captured_at,
            )
        elif isinstance(event, StandingsCaptured):
            self._read_models.upsert_standings(
                competition_id=event.competition_id,
                standings=event.standings,
                captured_at=event.captured_at,
            )
        elif isinstance(event, VenueCaptured):
            self._read_models.upsert_venue(
                venue_id=event.venue_id,
                name=event.name,
                city=event.city,
                country=event.country,
                capacity=event.capacity,
                captured_at=event.captured_at,
            )
        elif isinstance(event, RefereeCaptured):
            self._read_models.upsert_referee(
                referee_id=event.referee_id,
                name=event.name,
                country=event.country,
                details=event.details,
                captured_at=event.captured_at,
            )
        elif isinstance(event, PlayerStatsCaptured):
            self._read_models.upsert_player_stats(
                match_id=event.match_id, stats=event.stats, captured_at=event.captured_at,
            )
        elif isinstance(event, IncidentsCaptured):
            self._read_models.upsert_incidents(
                match_id=event.match_id, incidents=event.incidents, captured_at=event.captured_at,
            )
        else:
            logger.warning(f"unhandled domain event type: {type(event).__name__}")

    async def _evaluate_value_bet(self, match_id: object) -> None:
        """A bug in value-bet detection must never poison the message that
        triggered it — the odds/lineup write above already committed in its
        own transaction, so a failure here would otherwise nack an
        otherwise-valid message and send perfectly good data to the DLX
        (confirmed live: a probability-scale bug here turned every
        OddsComparisonCaptured for a match with an insight into a poison
        message)."""
        try:
            await self._value_bet_detector.evaluate(match_id)
        except Exception as exc:
            logger.error(f"value bet evaluation failed for match {match_id}: {exc}", exc_info=True)

    def _resolve_value_bet_outcomes(self, match_id: object, home_score: int, away_score: int) -> None:
        """Same isolation guarantee as _evaluate_value_bet — MatchFinished
        already committed above; a bug archiving value-bet outcomes must
        not turn a valid MatchFinished into a poison message."""
        try:
            self._value_bet_outcome_resolver.resolve_match(match_id, home_score, away_score)
        except Exception as exc:
            logger.error(f"value bet outcome resolution failed for match {match_id}: {exc}", exc_info=True)
