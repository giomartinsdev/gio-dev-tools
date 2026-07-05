from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from shared.events import (
    DomainEvent,
    EventMeta,
    MatchFinished,
    MatchScheduled,
    MatchScoreUpdated,
    MatchStatus,
    MatchStatusChanged,
    OddsSelection,
    OddsSnapshotCaptured,
)

from ..domain.repository import IdentityRepository

PROVIDER = "bzzoiro"
_PRODUCER = "acl.bzzoiro"

_STATUS_MAP = {
    "upcoming": MatchStatus.SCHEDULED,
    "live": MatchStatus.LIVE,
    "finished": MatchStatus.FINISHED,
    "postponed": MatchStatus.POSTPONED,
    "cancelled": MatchStatus.CANCELLED,
}


class BzzoiroTranslator:
    """The anti-corruption core: bzzoiro payload -> canonical domain events.

    provider_ref (bzzoiro's own id) is resolved to a canonical UUID via
    IdentityRepository and never appears on the events this returns.
    """

    def __init__(self, identity_repo: IdentityRepository):
        self._identity = identity_repo

    def _resolve(self, entity_type: str, provider_ref: object) -> object:
        return self._identity.get_or_create(PROVIDER, str(provider_ref), entity_type)

    def translate_event(self, payload: dict) -> list[DomainEvent]:
        match_id = self._resolve("match", payload.get("id"))
        competition_id = self._resolve("competition", (payload.get("league") or {}).get("id"))
        home = payload.get("home") or {}
        away = payload.get("away") or {}
        home_team_id = self._resolve("team", home.get("id"))
        away_team_id = self._resolve("team", away.get("id"))

        def _meta() -> EventMeta:
            return EventMeta(
                occurred_at=datetime.now(timezone.utc),
                producer=_PRODUCER,
                correlation_id=match_id,
            )

        events: list[DomainEvent] = []
        provider_status = ((payload.get("status") or {}).get("name") or "").lower()
        status = _STATUS_MAP.get(provider_status)

        kickoff_raw = payload.get("date") or payload.get("kickoff_at")
        if kickoff_raw and status == MatchStatus.SCHEDULED:
            kickoff_at = kickoff_raw if isinstance(kickoff_raw, datetime) else datetime.fromisoformat(kickoff_raw)
            events.append(MatchScheduled(
                meta=_meta(),
                match_id=match_id,
                competition_id=competition_id,
                home_team_id=home_team_id,
                away_team_id=away_team_id,
                kickoff_at=kickoff_at,
                venue=payload.get("venue"),
            ))

        if status is not None:
            events.append(MatchStatusChanged(
                meta=_meta(),
                match_id=match_id,
                status=status,
                minute=payload.get("minute"),
            ))

        score = payload.get("score") or {}
        if score:
            events.append(MatchScoreUpdated(
                meta=_meta(),
                match_id=match_id,
                home_score=int(score.get("home", 0)),
                away_score=int(score.get("away", 0)),
                minute=int(payload.get("minute") or 0),
            ))

        if status == MatchStatus.FINISHED:
            events.append(MatchFinished(
                meta=_meta(),
                match_id=match_id,
                home_score=int(score.get("home", 0)),
                away_score=int(score.get("away", 0)),
                statistics=payload.get("stats") or {},
            ))

        for market, selections in (payload.get("odds") or {}).items():
            if not isinstance(selections, dict):
                continue
            parsed = [
                OddsSelection(name=name, price=Decimal(str(price)))
                for name, price in selections.items()
                if price is not None
            ]
            if not parsed:
                continue
            events.append(OddsSnapshotCaptured(
                meta=_meta(),
                match_id=match_id,
                bookmaker="aggregate",
                market=market,
                selections=parsed,
                captured_at=datetime.now(timezone.utc),
            ))

        return events
