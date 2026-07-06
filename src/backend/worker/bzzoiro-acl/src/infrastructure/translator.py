from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from shared.events import (
    DomainEvent,
    EventMeta,
    InsightGenerated,
    MatchFinished,
    MatchScheduled,
    MatchScoreUpdated,
    MatchStatus,
    MatchStatusChanged,
    OddsSelection,
    OddsSnapshotCaptured,
    TeamUpdated,
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


def _parse_dt(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _summarize_recommendation(recommendations: dict) -> str:
    flags = []
    if recommendations.get("bet_favorite"):
        flags.append(f"favorite:{recommendations.get('favorite')}")
    if recommendations.get("over_15"):
        flags.append("over_1.5")
    if recommendations.get("over_25"):
        flags.append("over_2.5")
    if recommendations.get("over_35"):
        flags.append("over_3.5")
    if recommendations.get("btts"):
        flags.append("btts_yes")
    if recommendations.get("winner"):
        flags.append("winner")
    return ",".join(flags) if flags else "no_bet"


def _extract_status(raw: object) -> str:
    """bzzoiro's `status` field has been observed as both a plain string
    (`/api/events/`) and a `{"name": ...}` dict (WebSocket `event` frames).
    Accept either shape rather than assuming one."""
    if isinstance(raw, dict):
        return str(raw.get("name") or "")
    if isinstance(raw, str):
        return raw
    return ""


class BzzoiroTranslator:
    """The anti-corruption core: bzzoiro payload -> canonical domain events.

    provider_ref (bzzoiro's own id) is resolved to a canonical UUID via
    IdentityRepository and never appears on the events this returns.
    """

    def __init__(self, identity_repo: IdentityRepository):
        self._identity = identity_repo

    def _resolve(self, entity_type: str, provider_ref: object) -> object:
        return self._identity.get_or_create(PROVIDER, str(provider_ref), entity_type)

    def resolve_match_id(self, provider_ref: object) -> object:
        """Public helper so callers (e.g. poll handlers) can correlate a
        raw.feed_received record to the same canonical match_id the
        translated domain events will use, without reaching into _resolve."""
        return self._resolve("match", provider_ref)

    def resolve_team_id(self, provider_ref: object) -> object:
        """Public helper to resolve provider team ID to canonical UUID."""
        return self._resolve("team", provider_ref)

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
        provider_status = _extract_status(payload.get("status")).lower()
        status = _STATUS_MAP.get(provider_status)

        kickoff_raw = payload.get("date") or payload.get("kickoff_at")
        if kickoff_raw:
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

    def translate_odds_items(self, items: list[dict]) -> list[DomainEvent]:
        """GET /api/v2/odds/ returns a flat list — one row per
        (event, bookmaker, market, outcome). Group rows sharing an
        (event, bookmaker, market) into a single OddsSnapshotCaptured."""
        groups: dict[tuple, list[dict]] = {}
        for item in items:
            key = (item["event_id"], item["bookmaker_slug"], item["market"])
            groups.setdefault(key, []).append(item)

        match_id_cache: dict[object, object] = {}
        events: list[DomainEvent] = []
        for (event_id, bookmaker_slug, market), group in groups.items():
            if event_id not in match_id_cache:
                match_id_cache[event_id] = self._resolve("match", event_id)
            match_id = match_id_cache[event_id]

            selections = [
                OddsSelection(name=item["outcome"], price=Decimal(str(item["decimal_odds"])))
                for item in group
            ]
            captured_at = max(_parse_dt(item["updated_at"]) for item in group)

            events.append(OddsSnapshotCaptured(
                meta=EventMeta(
                    occurred_at=datetime.now(timezone.utc),
                    producer=_PRODUCER,
                    correlation_id=match_id,
                ),
                match_id=match_id,
                bookmaker=bookmaker_slug,
                market=market,
                selections=selections,
                captured_at=captured_at,
            ))
        return events

    def translate_prediction(self, payload: dict) -> InsightGenerated:
        """GET /api/v2/predictions/ -> one InsightGenerated per prediction.
        `feature_snapshot` keeps the full markets breakdown (match_result,
        expected_goals, over_under, btts, score) for later analysis."""
        event = payload["event"]
        match_id = self._resolve("match", event["id"])
        model = payload["model"]
        recommendations = payload["recommendations"]

        return InsightGenerated(
            meta=EventMeta(
                occurred_at=datetime.now(timezone.utc),
                producer=_PRODUCER,
                correlation_id=match_id,
            ),
            insight_id=uuid4(),
            match_id=match_id,
            market="match_result",
            recommendation=_summarize_recommendation(recommendations),
            confidence=Decimal(str(model["confidence"])),
            rationale=(
                f"favorite={recommendations.get('favorite')} "
                f"favorite_prob={recommendations.get('favorite_prob')}"
            ),
            model=model["version"],
            feature_snapshot=payload["markets"],
            generated_at=_parse_dt(payload["created_at"]),
        )

    def translate_team(self, payload: dict) -> TeamUpdated:
        """GET /api/v2/teams/ item -> TeamUpdated event."""
        team_id = self._resolve("team", payload.get("id"))
        return TeamUpdated(
            meta=EventMeta(
                occurred_at=datetime.now(timezone.utc),
                producer=_PRODUCER,
                correlation_id=team_id,
            ),
            team_id=team_id,
            name=payload.get("name") or "",
            code=payload.get("code"),
            logo=payload.get("logo"),
        )

