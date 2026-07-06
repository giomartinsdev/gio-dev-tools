from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Annotated, Literal, Optional, Union
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, TypeAdapter


class EventMeta(BaseModel):
    event_id: UUID = Field(default_factory=uuid4)
    occurred_at: datetime
    producer: str
    correlation_id: UUID
    causation_id: Optional[UUID] = None


class MatchStatus(str, Enum):
    SCHEDULED = "SCHEDULED"
    LIVE = "LIVE"
    FINISHED = "FINISHED"
    POSTPONED = "POSTPONED"
    CANCELLED = "CANCELLED"


class OddsSelection(BaseModel):
    name: str
    price: Decimal


class MatchScheduled(BaseModel):
    event_type: Literal["match.scheduled"] = "match.scheduled"
    version: Literal[1] = 1
    meta: EventMeta
    match_id: UUID
    competition_id: UUID
    home_team_id: UUID
    away_team_id: UUID
    kickoff_at: datetime
    venue: Optional[str] = None


class MatchStatusChanged(BaseModel):
    event_type: Literal["match.status_changed"] = "match.status_changed"
    version: Literal[1] = 1
    meta: EventMeta
    match_id: UUID
    status: MatchStatus
    minute: Optional[int] = None


class MatchScoreUpdated(BaseModel):
    event_type: Literal["match.score_updated"] = "match.score_updated"
    version: Literal[1] = 1
    meta: EventMeta
    match_id: UUID
    home_score: int
    away_score: int
    minute: int


class MatchFinished(BaseModel):
    event_type: Literal["match.finished"] = "match.finished"
    version: Literal[1] = 1
    meta: EventMeta
    match_id: UUID
    home_score: int
    away_score: int
    statistics: dict = Field(default_factory=dict)


class OddsSnapshotCaptured(BaseModel):
    event_type: Literal["odds.snapshot_captured"] = "odds.snapshot_captured"
    version: Literal[1] = 1
    meta: EventMeta
    match_id: UUID
    bookmaker: str
    market: str
    selections: list[OddsSelection]
    captured_at: datetime


class TeamUpdated(BaseModel):
    event_type: Literal["team.updated"] = "team.updated"
    version: Literal[1] = 1
    meta: EventMeta
    team_id: UUID
    name: str
    short_name: str
    country: str
    venue_id: Optional[int] = None


class SquadMember(BaseModel):
    squad_row_id: int
    player_id: Optional[UUID] = None
    name: str
    jersey_number: Optional[int] = None
    position: str
    status: str
    club: str
    club_country: str
    caps: Optional[int] = None
    goals: Optional[int] = None
    age: Optional[int] = None
    date_of_birth: Optional[str] = None


class SquadUpdated(BaseModel):
    event_type: Literal["team.squad_updated"] = "team.squad_updated"
    version: Literal[1] = 1
    meta: EventMeta
    team_id: UUID
    members: list[SquadMember]


class OddsComparisonCaptured(BaseModel):
    """GET /api/v2/events/{id}/odds/comparison/ — every bookmaker's price for
    every market/outcome of one match, plus the provider's own pick of the
    best price per outcome. Kept close to the wire shape (`markets` verbatim)
    rather than flattened, since domain-persister's value-bet detector reads
    `best_odds`/`best_bookmaker_slug` per outcome directly off of it."""

    event_type: Literal["odds.comparison_captured"] = "odds.comparison_captured"
    version: Literal[1] = 1
    meta: EventMeta
    match_id: UUID
    bookmakers_count: int
    total_odds: int
    markets: dict
    captured_at: datetime


class PolymarketSnapshotCaptured(BaseModel):
    """GET /api/v2/events/{id}/polymarket/ — prediction-market implied
    probabilities for one match, independent of both bookmaker odds and
    bzzoiro's own ML model. `markets` is kept as the raw provider shape:
    at the time this was written no live example ever returned data (every
    match probed returned "no markets available"), so the exact shape is
    unconfirmed — see bzzoiro-acl's translator for the defensive parsing."""

    event_type: Literal["polymarket.snapshot_captured"] = "polymarket.snapshot_captured"
    version: Literal[1] = 1
    meta: EventMeta
    match_id: UUID
    markets: dict
    captured_at: datetime


class OddsBestCaptured(BaseModel):
    """GET /api/v2/odds/best/ — best 1x2 price for one event, drawn from a
    single paginated list covering ALL events with tracked odds at once (one
    call for ~26 events observed live, vs. one call per event polling
    /odds/comparison/ requires). Only ever carries the "1x2" market —
    `markets` is always `{"1x2": {OUTCOME: {best_odds, best_bookmaker_slug,
    bookmakers}}}` — and is projected as a partial merge into the same
    `odds_comparisons` row `OddsComparisonCaptured` writes, never a full
    replace, so a cheap 1x2-only update can't wipe out over_under/btts data
    a fuller comparison already captured for the same match."""

    event_type: Literal["odds.best_captured"] = "odds.best_captured"
    version: Literal[1] = 1
    meta: EventMeta
    match_id: UUID
    markets: dict
    captured_at: datetime


class LineupsCaptured(BaseModel):
    """GET /api/v2/events/{id}/lineups/ — AI-predicted starting lineup per
    side, each with a `confidence` score and an overall `lineup_status`
    (`predicted` pre-kickoff, presumably `confirmed` once official team
    sheets drop). `lineups` is kept verbatim (`{"home": {...}, "away":
    {...}}`, each with `formation`/`confidence`/`players`) since the
    value-bet detector reads `confidence` directly off of it: a low-
    confidence predicted lineup means bzzoiro's own model and the market's
    odds may both have been computed before a real team-news surprise, so a
    detected edge could be stale noise rather than a real mispricing."""

    event_type: Literal["lineups.captured"] = "lineups.captured"
    version: Literal[1] = 1
    meta: EventMeta
    match_id: UUID
    lineup_status: str
    lineups: dict
    captured_at: datetime


class H2HCaptured(BaseModel):
    """GET /api/v2/events/{id}/h2h/ — head-to-head record between the two
    sides. Pure context for a future dashboard's "why" narrative — doesn't
    feed the edge calculation. Often all-zero for pairings with no shared
    history (confirmed live), so it's kept as a nullable snapshot rather
    than assumed always meaningful."""

    event_type: Literal["h2h.captured"] = "h2h.captured"
    version: Literal[1] = 1
    meta: EventMeta
    match_id: UUID
    h2h: dict
    captured_at: datetime


class StandingsCaptured(BaseModel):
    """GET /api/v2/leagues/{id}/standings/ — the league table at the time of
    capture. Keyed by competition, not match — same "why" context role as
    H2HCaptured, doesn't feed edge detection."""

    event_type: Literal["standings.captured"] = "standings.captured"
    version: Literal[1] = 1
    meta: EventMeta
    competition_id: UUID
    standings: dict
    captured_at: datetime


DomainEvent = Annotated[
    Union[
        MatchScheduled,
        MatchStatusChanged,
        MatchScoreUpdated,
        MatchFinished,
        OddsSnapshotCaptured,
        TeamUpdated,
        SquadUpdated,
        OddsComparisonCaptured,
        PolymarketSnapshotCaptured,
        OddsBestCaptured,
        LineupsCaptured,
        H2HCaptured,
        StandingsCaptured,
    ],
    Field(discriminator="event_type"),
]

domain_event_adapter: TypeAdapter[DomainEvent] = TypeAdapter(DomainEvent)


class RawFeedReceived(BaseModel):
    event_type: Literal["raw.feed_received"] = "raw.feed_received"
    version: Literal[1] = 1
    meta: EventMeta
    source: str
    feed_type: str
    provider_ref: str
    payload: dict


class InsightGenerated(BaseModel):
    event_type: Literal["analysis.insight_generated"] = "analysis.insight_generated"
    version: Literal[1] = 1
    meta: EventMeta
    insight_id: UUID
    match_id: UUID
    market: str
    recommendation: str
    confidence: Decimal
    rationale: str
    model: str
    feature_snapshot: dict
    generated_at: datetime
