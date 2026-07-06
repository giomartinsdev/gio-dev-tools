from __future__ import annotations

from decimal import Decimal
from uuid import UUID, uuid4

from behave import given, then, use_step_matcher, when

from shared.events import InsightGenerated, MatchScheduled, OddsSnapshotCaptured, TeamUpdated
from src.domain.repository import IdentityRepository
from src.infrastructure.translator import BzzoiroTranslator

use_step_matcher("re")


class _InMemoryIdentityRepository(IdentityRepository):
    def __init__(self):
        self._store: dict[tuple[str, str, str], UUID] = {}

    def get_or_create(self, provider: str, provider_ref: str, entity_type: str) -> UUID:
        key = (provider, provider_ref, entity_type)
        if key not in self._store:
            self._store[key] = uuid4()
        return self._store[key]


def _setup(context):
    context.identity_repo = _InMemoryIdentityRepository()
    context.translator = BzzoiroTranslator(context.identity_repo)
    context.odds_items = []
    context.odds_events = []
    context.prediction_payload = {}
    context.insight = None
    context.resolved_match_id = None


@given('a fresh translator for odds and predictions')
def step_fresh_translator(context):
    _setup(context)


@given(r'(\d+) v2 odds rows for event "([^"]+)" bookmaker "([^"]+)" market "([^"]+)" with outcomes home=([\d.]+) draw=([\d.]+) away=([\d.]+)')
def step_grouped_odds_rows(context, _count, event_id, bookmaker, market, home, draw, away):
    context.odds_items = [
        {"event_id": event_id, "bookmaker_slug": bookmaker, "market": market, "outcome": "HOME", "decimal_odds": home, "updated_at": "2026-08-01T10:00:00Z"},
        {"event_id": event_id, "bookmaker_slug": bookmaker, "market": market, "outcome": "DRAW", "decimal_odds": draw, "updated_at": "2026-08-01T10:00:01Z"},
        {"event_id": event_id, "bookmaker_slug": bookmaker, "market": market, "outcome": "AWAY", "decimal_odds": away, "updated_at": "2026-08-01T10:00:02Z"},
    ]


@given(r'v2 odds rows for event "([^"]+)" from bookmakers "([^"]+)" and "([^"]+)" both market "([^"]+)"')
def step_two_bookmaker_rows(context, event_id, bookmaker_a, bookmaker_b, market):
    context.odds_items = [
        {"event_id": event_id, "bookmaker_slug": bookmaker_a, "market": market, "outcome": "HOME", "decimal_odds": "2.10", "updated_at": "2026-08-01T10:00:00Z"},
        {"event_id": event_id, "bookmaker_slug": bookmaker_b, "market": market, "outcome": "HOME", "decimal_odds": "2.05", "updated_at": "2026-08-01T10:00:00Z"},
    ]


@when('I translate the odds rows')
def step_translate_odds(context):
    context.odds_events = context.translator.translate_odds_items(context.odds_items)


@then(r'(\d+) OddsSnapshotCaptured events? (?:is|are) produced with (\d+) selections')
def step_assert_one_snapshot_n_selections(context, event_count, selection_count):
    odds_events = [e for e in context.odds_events if isinstance(e, OddsSnapshotCaptured)]
    assert len(odds_events) == int(event_count), odds_events
    assert len(odds_events[0].selections) == int(selection_count), odds_events[0].selections


@then(r'(\d+) OddsSnapshotCaptured events? (?:is|are) produced')
def step_assert_n_snapshots(context, event_count):
    odds_events = [e for e in context.odds_events if isinstance(e, OddsSnapshotCaptured)]
    assert len(odds_events) == int(event_count), odds_events


@given(r'a v2 prediction payload for event "([^"]+)" with confidence ([\d.]+) recommending the favorite')
def step_prediction_favorite(context, event_id, confidence):
    context.prediction_payload = {
        "id": 1,
        "created_at": "2026-08-01T09:00:00Z",
        "event": {"id": event_id, "event_date": "2026-08-01T20:00:00Z", "status": "notstarted",
                   "home_team_id": 1, "home_team": "A", "away_team_id": 2, "away_team": "B",
                   "league_id": 1, "league_name": "L"},
        "markets": {"match_result": {"prob_home": 0.6, "prob_draw": 0.2, "prob_away": 0.2, "predicted": "H"}},
        "recommendations": {
            "favorite": "H", "favorite_prob": 0.6, "bet_favorite": True,
            "over_15": False, "over_25": False, "over_35": False, "btts": False, "winner": True,
        },
        "model": {"confidence": confidence, "version": "v4"},
    }


@given(r'a v2 prediction payload for event "([^"]+)" with confidence ([\d.]+) recommending nothing')
def step_prediction_no_bet(context, event_id, confidence):
    context.prediction_payload = {
        "id": 2,
        "created_at": "2026-08-01T09:00:00Z",
        "event": {"id": event_id, "event_date": "2026-08-01T20:00:00Z", "status": "notstarted",
                   "home_team_id": 1, "home_team": "A", "away_team_id": 2, "away_team": "B",
                   "league_id": 1, "league_name": "L"},
        "markets": {"match_result": {"prob_home": 0.34, "prob_draw": 0.33, "prob_away": 0.33, "predicted": None}},
        "recommendations": {
            "favorite": None, "favorite_prob": None, "bet_favorite": False,
            "over_15": False, "over_25": False, "over_35": False, "btts": False, "winner": False,
        },
        "model": {"confidence": confidence, "version": "v4"},
    }


@when('I translate the prediction')
def step_translate_prediction(context):
    context.insight = context.translator.translate_prediction(context.prediction_payload)


@then(r'an InsightGenerated event with confidence "([^"]+)" is produced')
def step_assert_insight(context, confidence):
    assert isinstance(context.insight, InsightGenerated)
    assert context.insight.confidence == Decimal(confidence), context.insight.confidence


@then('the recommendation mentions the favorite')
def step_assert_mentions_favorite(context):
    assert "favorite" in context.insight.recommendation, context.insight.recommendation


@then(r'the recommendation is "([^"]+)"')
def step_assert_recommendation(context, expected):
    assert context.insight.recommendation == expected, context.insight.recommendation


@when('I translate the prediction context')
def step_translate_prediction_context(context):
    context.context_events = context.translator.translate_prediction_context(
        context.prediction_payload["event"]
    )


@then('a MatchScheduled event is produced')
def step_assert_match_scheduled(context):
    matches = [e for e in context.context_events if isinstance(e, MatchScheduled)]
    assert len(matches) == 1, context.context_events


@then(r'a TeamUpdated event named "([^"]+)" is produced')
def step_assert_team_updated(context, name):
    teams = [e for e in context.context_events if isinstance(e, TeamUpdated) and e.name == name]
    assert len(teams) == 1, context.context_events


@when(r'I resolve the match id for provider_ref "([^"]+)"')
def step_resolve_match_id(context, provider_ref):
    context.resolved_match_id = context.translator.resolve_match_id(provider_ref)


@then("the resolved match id matches the snapshot's match id")
def step_assert_resolved_matches(context):
    odds_events = [e for e in context.odds_events if isinstance(e, OddsSnapshotCaptured)]
    assert odds_events, "no odds events to compare against"
    assert context.resolved_match_id == odds_events[0].match_id, \
        f"{context.resolved_match_id} != {odds_events[0].match_id}"
