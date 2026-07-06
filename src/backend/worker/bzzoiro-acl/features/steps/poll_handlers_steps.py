from __future__ import annotations

import asyncio
from uuid import UUID, uuid4

from behave import given, then, use_step_matcher, when

from src.application.commands.poll_fixtures import PollFixturesCommand, PollFixturesHandler
from src.application.commands.poll_live import PollLiveCommand, PollLiveHandler
from src.application.commands.poll_odds import PollOddsCommand, PollOddsHandler
from src.application.commands.poll_predictions import PollPredictionsCommand, PollPredictionsHandler
from src.application.commands.poll_teams import PollTeamsCommand, PollTeamsHandler
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


class _FakeClient:
    def __init__(self):
        self.events_payloads: list[dict] = []
        self.live_payloads: list[dict] = []
        self.odds_rows: list[dict] = []
        self.prediction_payloads: list[dict] = []
        self.teams_payloads: list[dict] = []
        self.squad_payloads: dict = {}
        self.fetch_teams_calls: int = 0
        self.odds_page_calls: list[tuple] = []

    def fetch_events(self, date_from=None, date_to=None, status=None):
        return self.events_payloads

    def fetch_live(self):
        return self.live_payloads

    def fetch_odds(self, updated_after=None):
        return self.odds_rows

    def fetch_odds_page(self, offset=0, limit=200, updated_after=None):
        self.odds_page_calls.append((offset, limit, updated_after))
        sliced = self.odds_rows[offset:offset+limit]
        has_next = (offset + limit) < len(self.odds_rows)
        return sliced, has_next

    def fetch_predictions(self, status="upcoming"):
        return self.prediction_payloads

    def fetch_teams(self) -> list[dict]:
        self.fetch_teams_calls += 1
        return self.teams_payloads

    def fetch_squad(self, team_ref_id: int) -> dict:
        return self.squad_payloads


class _FakeCheckpointRepository:
    def __init__(self):
        self._store: dict[str, str] = {}

    def get_cursor(self, feed_type):
        return self._store.get(feed_type)

    def set_cursor(self, feed_type, cursor):
        self._store[feed_type] = cursor

    def clear(self, feed_type):
        self._store.pop(feed_type, None)

    def clear_all(self):
        self._store.clear()


class _FakePublisher:
    def __init__(self):
        self.raw_calls: list[tuple] = []
        self.domain_events: list = []
        self.insights: list = []

    async def publish_raw(self, feed_type, provider_ref, payload, correlation_id=None):
        self.raw_calls.append((feed_type, provider_ref, payload, correlation_id))

    async def publish_domain_event(self, event):
        self.domain_events.append(event)

    async def publish_insight(self, event):
        self.insights.append(event)


_SAMPLE_PAYLOAD = {
    "id": "321",
    "status": {"name": "upcoming"},
    "home": {"id": "10"},
    "away": {"id": "20"},
    "league": {"id": "1"},
    "date": "2026-08-01T20:00:00+00:00",
    "score": {"home": 0, "away": 0},
}


def _setup(context):
    context.client = _FakeClient()
    context.translator = BzzoiroTranslator(_InMemoryIdentityRepository())
    context.publisher = _FakePublisher()
    context.checkpoints = _FakeCheckpointRepository()
    context.polled_count = None


@given('a fake client, translator and publisher')
def step_setup(context):
    _setup(context)


@given('the fake client returns 1 fixture payload')
def step_one_fixture(context):
    context.client.events_payloads = [dict(_SAMPLE_PAYLOAD)]


@given('the fake client returns no fixtures')
def step_no_fixtures(context):
    context.client.events_payloads = []


@given('the fake client returns 1 live payload')
def step_one_live(context):
    context.client.live_payloads = [dict(_SAMPLE_PAYLOAD, status={"name": "live"})]


@given('the fake client returns 3 odds rows for the same event/bookmaker/market')
def step_three_odds_rows(context):
    context.client.odds_rows = [
        {"event_id": "42", "bookmaker_slug": "bet365", "market": "1x2", "outcome": "HOME", "decimal_odds": "2.10", "updated_at": "2026-08-01T10:00:00Z"},
        {"event_id": "42", "bookmaker_slug": "bet365", "market": "1x2", "outcome": "DRAW", "decimal_odds": "3.40", "updated_at": "2026-08-01T10:00:01Z"},
        {"event_id": "42", "bookmaker_slug": "bet365", "market": "1x2", "outcome": "AWAY", "decimal_odds": "3.60", "updated_at": "2026-08-01T10:00:02Z"},
    ]


@given('the fake client returns no odds rows')
def step_no_odds_rows(context):
    context.client.odds_rows = []


@given('the fake client returns 1 prediction payload')
def step_one_prediction(context):
    context.client.prediction_payloads = [{
        "id": 1,
        "created_at": "2026-08-01T09:00:00Z",
        "event": {"id": "77", "event_date": "2026-08-01T20:00:00Z", "status": "notstarted",
                   "home_team_id": 1, "home_team": "A", "away_team_id": 2, "away_team": "B",
                   "league_id": 1, "league_name": "L"},
        "markets": {"match_result": {"prob_home": 0.6, "prob_draw": 0.2, "prob_away": 0.2, "predicted": "H"}},
        "recommendations": {
            "favorite": "H", "favorite_prob": 0.6, "bet_favorite": True,
            "over_15": False, "over_25": False, "over_35": False, "btts": False, "winner": True,
        },
        "model": {"confidence": 0.82, "version": "v4"},
    }]


@given('the fake client returns 1 team payload')
def step_one_team_payload(context):
    context.client.teams_payloads = [{"id": 444, "name": "Team ABC", "short_name": "ABC", "country": "Brazil", "venue_id": 12}]
    context.client.squad_payloads = {
        "team_id": 444,
        "count": 1,
        "players": [{
            "id": 1, "team_id": 444, "name": "Player One", "jersey_number": 10,
            "position": "ST", "status": "official", "club": "Club X", "club_country": "Brazil",
            "caps": 5, "goals": 2, "date_of_birth": "2000-01-01", "age": 26, "player_id": 123
        }]
    }


@given('the fake client returns no teams')
def step_no_teams(context):
    context.client.teams_payloads = []
    context.client.squad_payloads = {}


@given(r'an odds checkpoint of "([^"]+)" already exists')
def step_existing_odds_checkpoint(context, cursor):
    context.checkpoints.set_cursor("odds", cursor)


@given(r'a teams checkpoint from (\d+) seconds ago exists')
def step_existing_teams_checkpoint(context, seconds_ago):
    from datetime import datetime, timedelta, timezone
    last_sync = datetime.now(timezone.utc) - timedelta(seconds=int(seconds_ago))
    context.checkpoints.set_cursor("teams", last_sync.isoformat())


@when('I run the fixtures poll handler')
def step_run_fixtures(context):
    handler = PollFixturesHandler(context.client, context.translator, context.publisher)
    context.polled_count = asyncio.run(handler.handle(PollFixturesCommand()))


@when('I run the live poll handler')
def step_run_live(context):
    handler = PollLiveHandler(context.client, context.translator, context.publisher)
    context.polled_count = asyncio.run(handler.handle(PollLiveCommand()))


@when('I run the odds poll handler')
def step_run_odds(context):
    handler = PollOddsHandler(context.client, context.translator, context.publisher, context.checkpoints)
    context.polled_count = asyncio.run(handler.handle(PollOddsCommand()))


@when('I run the odds poll handler with force')
def step_run_odds_force(context):
    handler = PollOddsHandler(context.client, context.translator, context.publisher, context.checkpoints)
    context.polled_count = asyncio.run(handler.handle(PollOddsCommand(force=True)))


@when('I run the predictions poll handler')
def step_run_predictions(context):
    handler = PollPredictionsHandler(context.client, context.translator, context.publisher)
    context.polled_count = asyncio.run(handler.handle(PollPredictionsCommand()))


@when('I run the teams poll handler')
def step_run_teams(context):
    handler = PollTeamsHandler(context.client, context.translator, context.publisher, context.checkpoints)
    context.polled_count = asyncio.run(handler.handle(PollTeamsCommand()))


@when('I run the teams poll handler with force')
def step_run_teams_force(context):
    handler = PollTeamsHandler(context.client, context.translator, context.publisher, context.checkpoints)
    context.polled_count = asyncio.run(handler.handle(PollTeamsCommand(force=True)))


@then(r'(\d+) events? (?:was|were) polled')
def step_assert_count(context, expected):
    assert context.polled_count == int(expected), f"expected {expected}, got {context.polled_count}"


@then('the publisher recorded a raw publish and at least one domain event publish')
def step_assert_published(context):
    assert len(context.publisher.raw_calls) >= 1, context.publisher.raw_calls
    assert len(context.publisher.domain_events) >= 1, context.publisher.domain_events


@then('the publisher recorded a raw publish')
def step_assert_raw_published(context):
    assert len(context.publisher.raw_calls) >= 1, context.publisher.raw_calls


@then('the publisher recorded a raw publish and at least one insight publish')
def step_assert_insight_published(context):
    assert len(context.publisher.raw_calls) >= 1, context.publisher.raw_calls
    assert len(context.publisher.insights) >= 1, context.publisher.insights


@then('the publisher recorded no raw publish')
def step_assert_no_raw(context):
    assert context.publisher.raw_calls == []


@then(r'the odds checkpoint is (\S+)')
def step_assert_odds_checkpoint(context, expected):
    from datetime import datetime
    cursor = context.checkpoints.get_cursor("odds")
    if expected == "None":
        assert cursor is None, f"expected no checkpoint, got {cursor}"
    else:
        expected_dt = datetime.fromisoformat(expected)
        actual_dt = datetime.fromisoformat(cursor)
        assert actual_dt == expected_dt, f"expected {expected_dt!r}, got {actual_dt!r}"


@then(r'fetch_odds_page was called with updated_after (\S+)')
def step_assert_odds_page_updated_after(context, expected):
    from datetime import datetime
    assert context.client.odds_page_calls, "fetch_odds_page was never called"
    _, _, updated_after = context.client.odds_page_calls[0]
    if expected == "None":
        assert updated_after is None, f"expected None, got {updated_after}"
    else:
        assert updated_after == datetime.fromisoformat(expected), (
            f"expected {expected}, got {updated_after!r}"
        )


@then('fetch_teams was not called')
def step_assert_fetch_teams_not_called(context):
    assert context.client.fetch_teams_calls == 0, context.client.fetch_teams_calls


@then('fetch_teams was called')
def step_assert_fetch_teams_called(context):
    assert context.client.fetch_teams_calls >= 1, context.client.fetch_teams_calls


@then('a teams checkpoint was recorded')
def step_assert_teams_checkpoint_recorded(context):
    assert context.checkpoints.get_cursor("teams") is not None
