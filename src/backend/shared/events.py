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


DomainEvent = Annotated[
    Union[
        MatchScheduled,
        MatchStatusChanged,
        MatchScoreUpdated,
        MatchFinished,
        OddsSnapshotCaptured,
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
