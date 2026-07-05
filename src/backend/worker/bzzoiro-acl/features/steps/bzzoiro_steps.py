from __future__ import annotations

from decimal import Decimal
from uuid import UUID, uuid4

from behave import given, then, use_step_matcher, when

from shared.events import MatchFinished, MatchStatusChanged, OddsSnapshotCaptured
from src.domain.repository import IdentityRepository
from src.infrastructure.translator import BzzoiroTranslator

use_step_matcher("re")


class InMemoryIdentityRepository(IdentityRepository):
    def __init__(self):
        self._store: dict[tuple[str, str, str], UUID] = {}

    def get_or_create(self, provider: str, provider_ref: str, entity_type: str) -> UUID:
        key = (provider, provider_ref, entity_type)
        if key not in self._store:
            self._store[key] = uuid4()
        return self._store[key]


def _setup(context):
    context.identity_repo = InMemoryIdentityRepository()
    context.translator = BzzoiroTranslator(context.identity_repo)
    context.events = []
    context.payload = {}


@given('a fresh translator')
def step_fresh_translator(context):
    _setup(context)


@given(r'a bzzoiro event payload with id "([^"]+)" status "([^"]+)"')
def step_payload_with_status(context, provider_id, status):
    context.payload = {
        "id": provider_id,
        "status": {"name": status},
        "home": {"id": "10"},
        "away": {"id": "20"},
        "league": {"id": "1"},
        "date": "2026-08-01T20:00:00+00:00",
        "score": {"home": 0, "away": 0},
    }


@given(r'a bzzoiro event payload with id "([^"]+)" status "([^"]+)" score home (\d+) away (\d+)')
def step_payload_with_status_and_score(context, provider_id, status, home_score, away_score):
    context.payload = {
        "id": provider_id,
        "status": {"name": status},
        "home": {"id": "10"},
        "away": {"id": "20"},
        "league": {"id": "1"},
        "score": {"home": int(home_score), "away": int(away_score)},
    }


@given(r'a bzzoiro event payload with odds market "([^"]+)" price "([^"]+)" for selection "([^"]+)"')
def step_payload_with_odds(context, market, price, selection):
    context.payload = {
        "id": "999",
        "status": {"name": "live"},
        "home": {"id": "10"},
        "away": {"id": "20"},
        "league": {"id": "1"},
        "score": {"home": 1, "away": 0},
        "odds": {market: {selection: price}},
    }


@when('I translate the payload')
def step_translate(context):
    context.events = context.translator.translate_event(context.payload)


@then(r'a MatchStatusChanged event with status "([^"]+)" is produced')
def step_status_event(context, expected_status):
    matches = [e for e in context.events if isinstance(e, MatchStatusChanged)]
    assert matches, f"no MatchStatusChanged produced; events: {context.events}"
    assert matches[0].status.value == expected_status, \
        f"expected {expected_status}, got {matches[0].status.value}"


@then(r'no provider id leaks into the event')
def step_no_provider_leak(context):
    for event in context.events:
        dumped = event.model_dump(mode="json")
        assert context.payload["id"] not in str(dumped.get("match_id", "")), \
            "provider_ref leaked into canonical id"


@then(r'an OddsSnapshotCaptured event with a Decimal price of "([^"]+)" is produced')
def step_odds_event(context, expected_price):
    odds_events = [e for e in context.events if isinstance(e, OddsSnapshotCaptured)]
    assert odds_events, f"no odds event produced; events: {context.events}"
    prices = [sel.price for sel in odds_events[0].selections]
    assert Decimal(expected_price) in prices, f"expected price {expected_price} in {prices}"
    assert all(isinstance(p, Decimal) for p in prices), "odds prices must be Decimal"


@then(r'the same provider ref resolves to the same canonical match id')
def step_same_canonical_id(context):
    again = context.translator.translate_event(context.payload)
    first_ids = {e.match_id for e in context.events if hasattr(e, "match_id")}
    second_ids = {e.match_id for e in again if hasattr(e, "match_id")}
    assert first_ids == second_ids, f"expected same canonical ids, got {first_ids} vs {second_ids}"


@then(r'a MatchFinished event with home score (\d+) and away score (\d+) is produced')
def step_match_finished(context, home_score, away_score):
    finished = [e for e in context.events if isinstance(e, MatchFinished)]
    assert finished, f"no MatchFinished produced; events: {context.events}"
    assert finished[0].home_score == int(home_score)
    assert finished[0].away_score == int(away_score)


@given(r'a bzzoiro event payload with a malformed odds market "([^"]+)"')
def step_payload_malformed_odds(context, market):
    context.payload = {
        "id": "111",
        "status": {"name": "live"},
        "home": {"id": "10"},
        "away": {"id": "20"},
        "league": {"id": "1"},
        "score": {"home": 0, "away": 0},
        "odds": {market: "not-a-dict"},
    }


@given(r'a bzzoiro event payload with odds market "([^"]+)" where every price is null')
def step_payload_all_null_odds(context, market):
    context.payload = {
        "id": "112",
        "status": {"name": "live"},
        "home": {"id": "10"},
        "away": {"id": "20"},
        "league": {"id": "1"},
        "score": {"home": 0, "away": 0},
        "odds": {market: {"home": None, "away": None}},
    }


@then('no OddsSnapshotCaptured event is produced')
def step_no_odds_event(context):
    odds_events = [e for e in context.events if isinstance(e, OddsSnapshotCaptured)]
    assert not odds_events, f"expected no odds event, got: {odds_events}"
