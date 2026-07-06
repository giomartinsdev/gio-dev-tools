from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
from uuid import uuid4

from shared.events import (
    DomainEvent,
    EventMeta,
    H2HCaptured,
    IncidentsCaptured,
    InsightGenerated,
    LineupsCaptured,
    MatchFinished,
    MatchScheduled,
    MatchScoreUpdated,
    MatchStatus,
    MatchStatusChanged,
    OddsBestCaptured,
    OddsComparisonCaptured,
    OddsSelection,
    OddsSnapshotCaptured,
    PlayerStatsCaptured,
    PolymarketSnapshotCaptured,
    RefereeCaptured,
    StandingsCaptured,
    TeamUpdated,
    SquadMember,
    SquadUpdated,
    VenueCaptured,
)
from shared.logger import get_logger

from ..domain.repository import IdentityRepository

logger = get_logger(__name__)

PROVIDER = "bzzoiro"
_PRODUCER = "acl.bzzoiro"

_STATUS_MAP = {
    # Real v2 EventDetailV2Schema.status values (confirmed live against the
    # OpenAPI spec's status enum: 1st_half, 2nd_half, aet, cancelled,
    # extratime, finished, halftime, inprogress, notstarted, penalties,
    # postponed). "upcoming"/"live" are kept too since some other feeds
    # (predictions) use that v1-style vocabulary instead.
    "notstarted": MatchStatus.SCHEDULED,
    "upcoming": MatchStatus.SCHEDULED,
    "inprogress": MatchStatus.LIVE,
    "1st_half": MatchStatus.LIVE,
    "2nd_half": MatchStatus.LIVE,
    "halftime": MatchStatus.LIVE,
    "extratime": MatchStatus.LIVE,
    "aet": MatchStatus.LIVE,
    "penalties": MatchStatus.LIVE,
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

    def resolve_competition_id(self, provider_ref: object) -> object:
        """Public helper to resolve provider league/competition ID to
        canonical UUID."""
        return self._resolve("competition", provider_ref)

    def translate_event(self, payload: dict) -> list[DomainEvent]:
        """GET /api/v2/events/ (EventDetailV2Schema) -> domain events.

        Confirmed live against a real payload — the actual shape is flat:
        `home_team_id`/`away_team_id` (ints, no nested `home`/`away` dict),
        `event_date` (not `date`/`kickoff_at`), `league_id` (not a nested
        `league.id`), `home_score`/`away_score` (flat ints, not a nested
        `score` dict), `current_minute` (not `minute`). This function used
        to read the nested/renamed fields this schema never actually has,
        which meant `MatchScheduled` almost never fired for real fixtures
        (`kickoff_raw` was always `None`) — confirmed in production via the
        `matches` table sitting at a fraction of the real fixture count and
        never advancing. No `venue` name string exists on this payload,
        only `venue_id` — `venue` stays `None` until a venue-name lookup
        exists.
        """
        match_id = self._resolve("match", payload.get("id"))
        competition_id = self._resolve("competition", payload.get("league_id"))
        home_team_id = self._resolve("team", payload.get("home_team_id"))
        away_team_id = self._resolve("team", payload.get("away_team_id"))

        def _meta() -> EventMeta:
            return EventMeta(
                occurred_at=datetime.now(timezone.utc),
                producer=_PRODUCER,
                correlation_id=match_id,
            )

        events: list[DomainEvent] = []
        provider_status = _extract_status(payload.get("status")).lower()
        status = _STATUS_MAP.get(provider_status)
        minute = payload.get("current_minute")

        kickoff_raw = payload.get("event_date")
        if kickoff_raw:
            kickoff_at = kickoff_raw if isinstance(kickoff_raw, datetime) else datetime.fromisoformat(kickoff_raw)
            events.append(MatchScheduled(
                meta=_meta(),
                match_id=match_id,
                competition_id=competition_id,
                home_team_id=home_team_id,
                away_team_id=away_team_id,
                kickoff_at=kickoff_at,
                venue=None,
            ))

        if status is not None:
            events.append(MatchStatusChanged(
                meta=_meta(),
                match_id=match_id,
                status=status,
                minute=minute,
            ))

        home_score = payload.get("home_score")
        away_score = payload.get("away_score")
        if home_score is not None and away_score is not None:
            events.append(MatchScoreUpdated(
                meta=_meta(),
                match_id=match_id,
                home_score=int(home_score),
                away_score=int(away_score),
                minute=int(minute or 0),
            ))

        if status == MatchStatus.FINISHED and home_score is not None and away_score is not None:
            events.append(MatchFinished(
                meta=_meta(),
                match_id=match_id,
                home_score=int(home_score),
                away_score=int(away_score),
                statistics=payload.get("statistics") or {},
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

    def translate_prediction_context(self, event: dict) -> list[DomainEvent]:
        """`/api/v2/predictions/` embeds a full event sub-object per
        prediction (`id`, `event_date`, `status`, `league_id`,
        `home_team_id`/`home_team`, `away_team_id`/`away_team` — confirmed
        live, same shape `translate_event` already reads off the fixtures
        feed). Predictions cover every "upcoming" fixture with no date
        bound (293 matches in one poll, confirmed live) — a far wider set
        than PollFixturesHandler's 3-day window — so without this, an
        insight can point at a match_id that has no row in `matches`/
        `teams` yet, and any dashboard joining on those tables shows blank
        team names until the fixtures/teams polls eventually catch up
        (which teams poll, on its 24h interval, may take a while to do).
        This reuses translate_event for the match/status and translate_team
        (with a synthesized minimal payload — only name is ever known here)
        for both sides, so the read models are populated immediately
        instead of waiting on a separate feed to reach the same fixture.
        Team rows are only ever completed here, never regressed: a later
        real TeamUpdated from the teams poll upserts short_name/country/
        venue_id over these placeholder blanks."""
        events: list[DomainEvent] = list(self.translate_event(event))

        home_id, home_name = event.get("home_team_id"), event.get("home_team")
        if home_id is not None and home_name:
            events.append(self.translate_team({"id": home_id, "name": home_name}))

        away_id, away_name = event.get("away_team_id"), event.get("away_team")
        if away_id is not None and away_name:
            events.append(self.translate_team({"id": away_id, "name": away_name}))

        return events

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
            short_name=payload.get("short_name") or "",
            country=payload.get("country") or "",
            venue_id=payload.get("venue_id"),
        )

    def translate_squad(self, provider_team_id: int, squad_payloads: list[dict]) -> SquadUpdated:
        """GET /api/v2/teams/{id}/squad/ -> SquadUpdated event.

        Confirmed live against real teams (62-player and 7-player squads,
        0/69 players had any of the fields below): this endpoint's actual
        shape is only `id, name, short_name, position, jersey_number,
        nationality, date_of_birth` — no `status`/`club`/`club_country`/
        `caps`/`goals`/`player_id`. Those richer fields are real, but come
        from a different endpoint entirely (`/api/v2/worldcup/squads/`,
        national-team call-up lists), which this code was apparently
        written against by mistake. `item["id"]` here IS the player's own
        provider ref (confirmed: the same id resolves at
        `/api/v2/players/{id}/`), not a distinct `player_id` field, so it's
        used for both `squad_row_id` and player identity resolution.
        """
        team_id = self._resolve("team", provider_team_id)
        members = []
        for item in squad_payloads:
            members.append(
                SquadMember(
                    squad_row_id=item["id"],
                    player_id=self._resolve("player", item["id"]),
                    name=item["name"],
                    jersey_number=item.get("jersey_number"),
                    position=item.get("position") or "",
                    status=item.get("status") or "active",
                    club=item.get("club") or "",
                    club_country=item.get("club_country") or "",
                    caps=item.get("caps"),
                    goals=item.get("goals"),
                    age=item.get("age"),
                    date_of_birth=item.get("date_of_birth"),
                )
            )
        
        return SquadUpdated(
            meta=EventMeta(
                occurred_at=datetime.now(timezone.utc),
                producer=_PRODUCER,
                correlation_id=team_id,
            ),
            team_id=team_id,
            members=members,
        )

    def translate_odds_comparison(self, payload: dict) -> OddsComparisonCaptured:
        """GET /api/v2/events/{id}/odds/comparison/ -> OddsComparisonCaptured.
        `markets` is kept verbatim (per-market -> per-outcome -> best price +
        per-bookmaker breakdown) since that's exactly the shape the value-bet
        detector in domain-persister needs."""
        match_id = self._resolve("match", payload.get("event_id"))
        return OddsComparisonCaptured(
            meta=EventMeta(
                occurred_at=datetime.now(timezone.utc),
                producer=_PRODUCER,
                correlation_id=match_id,
            ),
            match_id=match_id,
            bookmakers_count=int(payload.get("bookmakers_count") or 0),
            total_odds=int(payload.get("total_odds") or 0),
            markets=payload.get("markets") or {},
            captured_at=datetime.now(timezone.utc),
        )

    def translate_polymarket(self, event_ref_id: object, payload: dict) -> Optional[PolymarketSnapshotCaptured]:
        """GET /api/v2/events/{id}/polymarket/ -> PolymarketSnapshotCaptured.

        No live example ever returned real market data while this was
        written (every event probed returned bzzoiro's "no markets
        available" body) — the client already turns that specific 404 into
        `None` before this is called, but this stays defensive against a
        200 with the same error shape rather than assuming a schema we've
        never actually seen.
        """
        if not isinstance(payload, dict) or not payload:
            return None
        if "detail" in payload and len(payload) == 1:
            logger.info(f"polymarket: no markets available for event {event_ref_id}")
            return None

        match_id = self._resolve("match", event_ref_id)
        return PolymarketSnapshotCaptured(
            meta=EventMeta(
                occurred_at=datetime.now(timezone.utc),
                producer=_PRODUCER,
                correlation_id=match_id,
            ),
            match_id=match_id,
            markets=payload,
            captured_at=datetime.now(timezone.utc),
        )

    def translate_lineups(self, event_ref_id: object, payload: dict) -> Optional[LineupsCaptured]:
        """GET /api/v2/events/{id}/lineups/ -> LineupsCaptured.

        `lineups` kept verbatim (`{"home": {...}, "away": {...}}`, each with
        `formation`/`confidence`/`players`) since the value-bet detector
        reads `confidence` per side directly off of it."""
        if not isinstance(payload, dict) or not isinstance(payload.get("lineups"), dict):
            return None

        match_id = self._resolve("match", event_ref_id)
        return LineupsCaptured(
            meta=EventMeta(
                occurred_at=datetime.now(timezone.utc),
                producer=_PRODUCER,
                correlation_id=match_id,
            ),
            match_id=match_id,
            lineup_status=str(payload.get("lineup_status") or "unknown"),
            lineups=payload["lineups"],
            captured_at=datetime.now(timezone.utc),
        )

    def translate_h2h(self, event_ref_id: object, payload: dict) -> Optional[H2HCaptured]:
        """GET /api/v2/events/{id}/h2h/ -> H2HCaptured.

        Confirmed live: pairings with no shared history return a 200 with
        every field zeroed/null rather than a 404 — that's still a valid,
        meaningful capture (it says "these two have never met"), not an
        error, so it's translated the same as a populated one."""
        if not isinstance(payload, dict):
            return None

        match_id = self._resolve("match", event_ref_id)
        return H2HCaptured(
            meta=EventMeta(
                occurred_at=datetime.now(timezone.utc),
                producer=_PRODUCER,
                correlation_id=match_id,
            ),
            match_id=match_id,
            h2h=payload,
            captured_at=datetime.now(timezone.utc),
        )

    def translate_odds_best(self, payload: dict) -> Optional[OddsBestCaptured]:
        """GET /api/v2/odds/best/ (one row) -> OddsBestCaptured.

        Only the "1x2" market is ever present on this endpoint — `markets`
        is built to match the same per-outcome shape
        `OddsComparisonCaptured` uses (`best_odds`/`best_bookmaker_slug`),
        minus the per-bookmaker breakdown this leaner feed doesn't carry,
        so domain-persister's merge-not-replace projection can slot it into
        the same JSONB column without a shape mismatch."""
        event_ref_id = payload.get("event_id")
        if event_ref_id is None:
            return None

        outcomes: dict = {}
        for item in payload.get("best_odds") or []:
            outcome = item.get("outcome")
            decimal_odds = item.get("decimal_odds")
            bookmaker_slug = item.get("bookmaker_slug")
            if not outcome or not decimal_odds or not bookmaker_slug:
                continue
            outcomes[outcome] = {
                "best_odds": decimal_odds,
                "best_bookmaker_slug": bookmaker_slug,
                "bookmakers": {},
            }
        if not outcomes:
            return None

        match_id = self._resolve("match", event_ref_id)
        return OddsBestCaptured(
            meta=EventMeta(
                occurred_at=datetime.now(timezone.utc),
                producer=_PRODUCER,
                correlation_id=match_id,
            ),
            match_id=match_id,
            markets={"1x2": outcomes},
            captured_at=datetime.now(timezone.utc),
        )

    def translate_standings(self, league_ref_id: object, payload: dict) -> Optional[StandingsCaptured]:
        """GET /api/v2/leagues/{id}/standings/ -> StandingsCaptured.

        Resolved under the `"competition"` entity type (not `"league"`) to
        match the identity mapping `translate_event` already uses for the
        same provider concept — a separate `"league"` type would silently
        create a second, disconnected identity for the same real-world
        competition."""
        if not isinstance(payload, dict):
            return None

        competition_id = self._resolve("competition", league_ref_id)
        return StandingsCaptured(
            meta=EventMeta(
                occurred_at=datetime.now(timezone.utc),
                producer=_PRODUCER,
                correlation_id=competition_id,
            ),
            competition_id=competition_id,
            standings=payload,
            captured_at=datetime.now(timezone.utc),
        )

    def resolve_venue_id(self, provider_ref: object) -> object:
        """Public helper so poll handlers can correlate a raw.feed_received
        record to the same canonical venue_id the translated event uses."""
        return self._resolve("venue", provider_ref)

    def resolve_referee_id(self, provider_ref: object) -> object:
        """Public helper, same purpose as resolve_venue_id but for referees."""
        return self._resolve("referee", provider_ref)

    def translate_venue(self, venue_ref_id: object, payload: dict) -> Optional[VenueCaptured]:
        """GET /api/v2/venues/{id}/ -> VenueCaptured.

        Confirmed live: `id`, `name`, `city`, `country`, `capacity` (plus
        pitch/geo fields this doesn't need). Exists so `MatchScheduled.venue`
        can eventually carry a real name — the events feed only ever has
        `venue_id`, never a name string."""
        if not isinstance(payload, dict) or not payload.get("name"):
            return None

        venue_id = self._resolve("venue", venue_ref_id)
        return VenueCaptured(
            meta=EventMeta(
                occurred_at=datetime.now(timezone.utc),
                producer=_PRODUCER,
                correlation_id=venue_id,
            ),
            venue_id=str(venue_id),
            name=payload["name"],
            city=payload.get("city"),
            country=payload.get("country"),
            capacity=payload.get("capacity"),
            captured_at=datetime.now(timezone.utc),
        )

    def translate_referee(self, referee_ref_id: object, payload: dict) -> Optional[RefereeCaptured]:
        """GET /api/v2/referees/{id}/ -> RefereeCaptured.

        Confirmed live: `id`, `name`, `country`, plus career/season card and
        foul tendency stats — kept verbatim in `details` since which of
        those fields matter for a future "referee tendency" narrative isn't
        settled yet."""
        if not isinstance(payload, dict) or not payload.get("name"):
            return None

        referee_id = self._resolve("referee", referee_ref_id)
        return RefereeCaptured(
            meta=EventMeta(
                occurred_at=datetime.now(timezone.utc),
                producer=_PRODUCER,
                correlation_id=referee_id,
            ),
            referee_id=str(referee_id),
            name=payload["name"],
            country=payload.get("country"),
            details=payload,
            captured_at=datetime.now(timezone.utc),
        )

    def translate_player_stats(self, event_ref_id: object, payload: dict) -> Optional[PlayerStatsCaptured]:
        """GET /api/v2/events/{id}/player-stats/ -> PlayerStatsCaptured.

        Confirmed live: `{"event_id", "count", "player_stats": [...]}`, one
        entry per player who featured. Kept verbatim as one blob — only ever
        populated post-kickoff, so this is review context, not pre-match
        edge detection."""
        if not isinstance(payload, dict) or "player_stats" not in payload:
            return None

        match_id = self._resolve("match", event_ref_id)
        return PlayerStatsCaptured(
            meta=EventMeta(
                occurred_at=datetime.now(timezone.utc),
                producer=_PRODUCER,
                correlation_id=match_id,
            ),
            match_id=match_id,
            stats=payload,
            captured_at=datetime.now(timezone.utc),
        )

    def translate_incidents(self, event_ref_id: object, payload: dict) -> Optional[IncidentsCaptured]:
        """GET /api/v2/events/{id}/incidents/ -> IncidentsCaptured.

        Confirmed live: `{"event_id", "incidents": [...]}`, each entry a
        goal/card/substitution/period-marker. An empty `incidents` list is
        still a valid capture (a scoreless match with no cards/subs yet),
        so this checks key presence, not truthiness."""
        if not isinstance(payload, dict) or "incidents" not in payload:
            return None

        match_id = self._resolve("match", event_ref_id)
        return IncidentsCaptured(
            meta=EventMeta(
                occurred_at=datetime.now(timezone.utc),
                producer=_PRODUCER,
                correlation_id=match_id,
            ),
            match_id=match_id,
            incidents=payload,
            captured_at=datetime.now(timezone.utc),
        )


