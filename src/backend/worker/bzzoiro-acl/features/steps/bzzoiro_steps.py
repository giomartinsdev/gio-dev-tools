from __future__ import annotations

from uuid import UUID, uuid4

from behave import given, then, use_step_matcher, when

from shared.events import MatchFinished, MatchScheduled, MatchStatusChanged
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
    # bzzoiro's real /api/v2/events/ response (EventDetailV2Schema,
    # confirmed live) is flat: home_team_id/away_team_id (no nested
    # home/away dict), league_id (no nested league dict), event_date (not
    # date/kickoff_at), and status is a plain string.
    context.payload = {
        "id": provider_id,
        "status": status,
        "home_team_id": "10",
        "away_team_id": "20",
        "league_id": "1",
        "event_date": "2026-08-01T20:00:00+00:00",
        "home_score": None,
        "away_score": None,
    }


@given(r'a bzzoiro event payload with id "([^"]+)" status "([^"]+)" score home (\d+) away (\d+)')
def step_payload_with_status_and_score(context, provider_id, status, home_score, away_score):
    context.payload = {
        "id": provider_id,
        "status": status,
        "home_team_id": "10",
        "away_team_id": "20",
        "league_id": "1",
        "home_score": int(home_score),
        "away_score": int(away_score),
    }


@given(r'a bzzoiro event payload with id "([^"]+)" and dict-shaped status "([^"]+)"')
def step_payload_with_dict_status(context, provider_id, status):
    # Back-compat: WebSocket "event" frames nest status as {"name": ...}.
    context.payload = {
        "id": provider_id,
        "status": {"name": status},
        "home_team_id": "10",
        "away_team_id": "20",
        "league_id": "1",
        "home_score": None,
        "away_score": None,
    }


@given(r'a bzzoiro event payload with id "([^"]+)" and no status field at all')
def step_payload_without_status(context, provider_id):
    context.payload = {
        "id": provider_id,
        "home_team_id": "10",
        "away_team_id": "20",
        "league_id": "1",
        "home_score": None,
        "away_score": None,
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


@then('a MatchScheduled event with a kickoff time is produced')
def step_scheduled_event(context):
    matches = [e for e in context.events if isinstance(e, MatchScheduled)]
    assert matches, f"no MatchScheduled produced; events: {context.events}"
    assert matches[0].kickoff_at is not None
    assert matches[0].home_team_id is not None
    assert matches[0].away_team_id is not None
    assert matches[0].competition_id is not None


@then(r'no provider id leaks into the event')
def step_no_provider_leak(context):
    for event in context.events:
        dumped = event.model_dump(mode="json")
        assert context.payload["id"] not in str(dumped.get("match_id", "")), \
            "provider_ref leaked into canonical id"


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


@then('no MatchStatusChanged event is produced')
def step_no_status_event(context):
    status_events = [e for e in context.events if isinstance(e, MatchStatusChanged)]
    assert not status_events, f"expected no status event, got: {status_events}"
