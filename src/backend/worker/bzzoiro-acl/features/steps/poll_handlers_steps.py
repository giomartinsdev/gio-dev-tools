from __future__ import annotations

import asyncio
from uuid import UUID, uuid4

from behave import given, then, use_step_matcher, when

from src.application.commands.poll_fixtures import PollFixturesCommand, PollFixturesHandler
from src.application.commands.poll_h2h import PollH2HCommand, PollH2HHandler
from src.application.commands.poll_incidents import PollIncidentsCommand, PollIncidentsHandler
from src.application.commands.poll_lineups import PollLineupsCommand, PollLineupsHandler
from src.application.commands.poll_live import PollLiveCommand, PollLiveHandler
from src.application.commands.poll_odds import PollOddsCommand, PollOddsHandler
from src.application.commands.poll_odds_best import PollOddsBestCommand, PollOddsBestHandler
from src.application.commands.poll_odds_comparison import PollOddsComparisonCommand, PollOddsComparisonHandler
from src.application.commands.poll_player_stats import PollPlayerStatsCommand, PollPlayerStatsHandler
from src.application.commands.poll_predictions import PollPredictionsCommand, PollPredictionsHandler
from src.application.commands.poll_referees import PollRefereesCommand, PollRefereesHandler
from src.application.commands.poll_standings import PollStandingsCommand, PollStandingsHandler
from src.application.commands.poll_teams import PollTeamsCommand, PollTeamsHandler
from src.application.commands.poll_venues import PollVenuesCommand, PollVenuesHandler
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
        self.odds_comparison_by_event: dict = {}
        self.polymarket_by_event: dict = {}
        self.raise_on_comparison_for: set = set()
        self.odds_best_rows: list[dict] = []
        self.lineups_by_event: dict = {}
        self.h2h_by_event: dict = {}
        self.standings_by_league: dict = {}
        self.venue_by_id: dict = {}
        self.referee_by_id: dict = {}
        self.player_stats_by_event: dict = {}
        self.incidents_by_event: dict = {}

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

    def fetch_odds_comparison(self, event_ref_id):
        if event_ref_id in self.raise_on_comparison_for:
            raise TimeoutError("simulated transient network failure")
        return self.odds_comparison_by_event.get(event_ref_id)

    def fetch_polymarket(self, event_ref_id):
        return self.polymarket_by_event.get(event_ref_id)

    def fetch_odds_best(self) -> list[dict]:
        return self.odds_best_rows

    def fetch_lineups(self, event_ref_id):
        return self.lineups_by_event.get(event_ref_id)

    def fetch_h2h(self, event_ref_id):
        return self.h2h_by_event.get(event_ref_id)

    def fetch_standings(self, league_ref_id):
        return self.standings_by_league.get(league_ref_id)

    def fetch_venue(self, venue_ref_id):
        return self.venue_by_id.get(venue_ref_id)

    def fetch_referee(self, referee_ref_id):
        return self.referee_by_id.get(referee_ref_id)

    def fetch_player_stats(self, event_ref_id):
        return self.player_stats_by_event.get(event_ref_id)

    def fetch_incidents(self, event_ref_id):
        return self.incidents_by_event.get(event_ref_id)


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


@given('the fake client returns 1 fixture in the date window with odds comparison and polymarket data')
def step_one_fixture_with_comparison(context):
    context.client.events_payloads = [dict(_SAMPLE_PAYLOAD, id="900")]
    context.client.odds_comparison_by_event["900"] = {
        "event_id": "900", "bookmakers_count": 3, "total_odds": 10,
        "markets": {"1x2": {"HOME": {"best_odds": 2.1, "best_bookmaker_slug": "bet365", "bookmakers": {}}}},
    }
    context.client.polymarket_by_event["900"] = {"markets": {"1x2": {"HOME": 0.55}}}


@given('the fake client returns 1 fixture in the date window with no odds comparison or polymarket data')
def step_one_fixture_without_comparison(context):
    context.client.events_payloads = [dict(_SAMPLE_PAYLOAD, id="901")]


@given('the fake client returns 2 fixtures in the date window, one of which always raises on odds comparison')
def step_two_fixtures_one_raising(context):
    context.client.events_payloads = [dict(_SAMPLE_PAYLOAD, id="902"), dict(_SAMPLE_PAYLOAD, id="903")]
    context.client.raise_on_comparison_for = {"902"}
    context.client.odds_comparison_by_event["903"] = {
        "event_id": "903", "bookmakers_count": 3, "total_odds": 10,
        "markets": {"1x2": {"HOME": {"best_odds": 2.1, "best_bookmaker_slug": "bet365", "bookmakers": {}}}},
    }
    context.client.polymarket_by_event["903"] = {"markets": {"1x2": {"HOME": 0.55}}}


@given('the fake client returns 1 fixture in the date window with a lineup')
def step_one_fixture_with_lineup(context):
    context.client.events_payloads = [dict(_SAMPLE_PAYLOAD, id="910")]
    context.client.lineups_by_event["910"] = {
        "lineup_status": "predicted",
        "lineups": {"home": {"confidence": 0.8}, "away": {"confidence": 0.7}},
    }


@given('the fake client returns 1 fixture in the date window with no lineup yet')
def step_one_fixture_without_lineup(context):
    context.client.events_payloads = [dict(_SAMPLE_PAYLOAD, id="911")]


@given('the fake client returns 1 fixture in the date window with h2h history')
def step_one_fixture_with_h2h(context):
    context.client.events_payloads = [dict(_SAMPLE_PAYLOAD, id="920")]
    context.client.h2h_by_event["920"] = {"total_matches": 5, "home_wins": 2, "draws": 1, "away_wins": 2}


@given('the fake client returns 1 event with 1x2 odds via odds/best')
def step_one_odds_best_row(context):
    context.client.odds_best_rows = [{
        "event_id": "930",
        "best_odds": [
            {"outcome": "HOME", "decimal_odds": 2.1, "bookmaker_slug": "pinnacle"},
            {"outcome": "DRAW", "decimal_odds": 3.4, "bookmaker_slug": "bet365"},
            {"outcome": "AWAY", "decimal_odds": 3.9, "bookmaker_slug": "pinnacle"},
        ],
    }]


@given('the fake client returns 1 fixture in the date window with league 40 standings')
def step_one_fixture_with_standings(context):
    context.client.events_payloads = [dict(_SAMPLE_PAYLOAD, id="940", league_id=40)]
    context.client.standings_by_league[40] = {
        "league_id": 40, "standings": [{"team_id": 1, "position": 1, "points": 30}],
    }


@given('the fake client returns 1 fixture in the date window with no league_id')
def step_one_fixture_without_league_id(context):
    context.client.events_payloads = [dict(_SAMPLE_PAYLOAD, id="941")]


@given('the fake client returns 1 fixture in the date window with venue 735 detail')
def step_one_fixture_with_venue(context):
    context.client.events_payloads = [dict(_SAMPLE_PAYLOAD, id="950", venue_id=735)]
    context.client.venue_by_id[735] = {
        "id": 735, "name": "Estadio Municipal de Butarque", "city": "Leganes",
        "country": "Spain", "capacity": 12454,
    }


@given('the fake client returns 1 fixture in the date window with no venue_id')
def step_one_fixture_without_venue_id(context):
    context.client.events_payloads = [dict(_SAMPLE_PAYLOAD, id="951")]


@given('the fake client returns 1 fixture in the date window with referee 2535 detail')
def step_one_fixture_with_referee(context):
    context.client.events_payloads = [dict(_SAMPLE_PAYLOAD, id="960", referee_id=2535)]
    context.client.referee_by_id[2535] = {
        "id": 2535, "name": "Alireza Faghani", "country": "Australia",
        "avg_yellow_per_match": 3.31, "avg_red_per_match": 0.15,
    }


@given('the fake client returns 1 fixture in the date window with no referee_id')
def step_one_fixture_without_referee_id(context):
    context.client.events_payloads = [dict(_SAMPLE_PAYLOAD, id="961")]


@given('the fake client returns 1 finished fixture in the date window with player stats')
def step_one_finished_fixture_with_player_stats(context):
    context.client.events_payloads = [dict(_SAMPLE_PAYLOAD, id="970", status="finished")]
    context.client.player_stats_by_event["970"] = {
        "event_id": "970", "count": 1,
        "player_stats": [{"id": 1, "player_id": 10, "team_id": 1, "minutes_played": 90, "rating": 7.1}],
    }


@given('the fake client returns 1 fixture in the date window that has not kicked off')
def step_one_fixture_not_kicked_off(context):
    context.client.events_payloads = [dict(_SAMPLE_PAYLOAD, id="971", status="notstarted")]


@given('the fake client returns 1 finished fixture in the date window with incidents')
def step_one_finished_fixture_with_incidents(context):
    context.client.events_payloads = [dict(_SAMPLE_PAYLOAD, id="980", status="finished")]
    context.client.incidents_by_event["980"] = {
        "event_id": "980",
        "incidents": [{"type": "period", "text": "FT", "minute": 90, "home_score": 2, "away_score": 1}],
    }


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
        # Confirmed live: /api/v2/teams/{id}/squad/ never sends
        # status/club/club_country/player_id — those come from a different
        # endpoint (/api/v2/worldcup/squads/, national-team call-ups).
        "players": [{
            "id": 1, "name": "Player One", "short_name": "P. One", "jersey_number": 10,
            "position": "ST", "nationality": "Brazil", "date_of_birth": "2000-01-01",
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


@when('I run the odds comparison poll handler')
def step_run_odds_comparison(context):
    handler = PollOddsComparisonHandler(context.client, context.translator, context.publisher)
    context.polled_count = asyncio.run(handler.handle(PollOddsComparisonCommand()))


@when('I run the lineups poll handler')
def step_run_lineups(context):
    handler = PollLineupsHandler(context.client, context.translator, context.publisher)
    context.polled_count = asyncio.run(handler.handle(PollLineupsCommand()))


@when('I run the h2h poll handler')
def step_run_h2h(context):
    handler = PollH2HHandler(context.client, context.translator, context.publisher)
    context.polled_count = asyncio.run(handler.handle(PollH2HCommand()))


@when('I run the odds best poll handler')
def step_run_odds_best(context):
    handler = PollOddsBestHandler(context.client, context.translator, context.publisher)
    context.polled_count = asyncio.run(handler.handle(PollOddsBestCommand()))


@when('I run the standings poll handler')
def step_run_standings(context):
    handler = PollStandingsHandler(context.client, context.translator, context.publisher)
    context.polled_count = asyncio.run(handler.handle(PollStandingsCommand()))


@when('I run the teams poll handler')
def step_run_teams(context):
    handler = PollTeamsHandler(context.client, context.translator, context.publisher, context.checkpoints)
    context.polled_count = asyncio.run(handler.handle(PollTeamsCommand()))


@when('I run the teams poll handler with force')
def step_run_teams_force(context):
    handler = PollTeamsHandler(context.client, context.translator, context.publisher, context.checkpoints)
    context.polled_count = asyncio.run(handler.handle(PollTeamsCommand(force=True)))


@when('I run the venues poll handler')
def step_run_venues(context):
    handler = PollVenuesHandler(context.client, context.translator, context.publisher)
    context.polled_count = asyncio.run(handler.handle(PollVenuesCommand()))


@when('I run the referees poll handler')
def step_run_referees(context):
    handler = PollRefereesHandler(context.client, context.translator, context.publisher)
    context.polled_count = asyncio.run(handler.handle(PollRefereesCommand()))


@when('I run the player stats poll handler')
def step_run_player_stats(context):
    handler = PollPlayerStatsHandler(context.client, context.translator, context.publisher)
    context.polled_count = asyncio.run(handler.handle(PollPlayerStatsCommand()))


@when('I run the incidents poll handler')
def step_run_incidents(context):
    handler = PollIncidentsHandler(context.client, context.translator, context.publisher)
    context.polled_count = asyncio.run(handler.handle(PollIncidentsCommand()))


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


@then(r'the publisher recorded a raw publish for "([^"]+)" and a raw publish for "([^"]+)"')
def step_assert_raw_for_feed_types(context, feed_type_a, feed_type_b):
    feed_types = [call[0] for call in context.publisher.raw_calls]
    assert feed_type_a in feed_types, feed_types
    assert feed_type_b in feed_types, feed_types


@then(r'the publisher recorded a raw publish for "([^"]+)"')
def step_assert_raw_for_one_feed_type(context, feed_type):
    feed_types = [call[0] for call in context.publisher.raw_calls]
    assert feed_type in feed_types, feed_types


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
