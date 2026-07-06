from __future__ import annotations

from unittest.mock import Mock, patch

import httpcore
import httpx
from behave import given, then, use_step_matcher, when

import src.infrastructure.bzzoiro_client as bzzoiro_client_module
from src.infrastructure.bzzoiro_client import BzzoiroAuthError, BzzoiroClient, BzzoiroTransientError

use_step_matcher("re")


def _response(status_code: int, json_body: dict, headers: dict | None = None) -> Mock:
    resp = Mock(spec=httpx.Response)
    resp.status_code = status_code
    resp.headers = headers or {}
    resp.json.return_value = json_body

    def _raise_for_status():
        if status_code >= 400 and status_code not in (401, 403, 404, 429):
            raise httpx.HTTPStatusError("error", request=Mock(), response=resp)

    resp.raise_for_status.side_effect = _raise_for_status
    return resp


def _setup(context):
    context.client = BzzoiroClient(api_key="test-key")
    context.result = None
    context.error = None


@given('a fresh bzzoiro client')
def step_fresh_client(context):
    _setup(context)


@given('a bzzoiro v2 API that returns 2 pages of events as envelope')
def step_v2_two_event_pages(context):
    _setup(context)
    page1 = _response(200, {"count": 4, "next": "https://x/?offset=200", "previous": None, "results": [{"id": 1}, {"id": 2}]})
    page2 = _response(200, {"count": 4, "next": None, "previous": "...", "results": [{"id": 3}, {"id": 4}]})
    context.get_patch = patch.object(httpx.Client, "get", side_effect=[page1, page2])


@given('a bzzoiro v2 API that returns 1 flat page of events')
def step_v2_flat_events_page(context):
    _setup(context)
    context.max_page_size_patch = patch.object(bzzoiro_client_module, "_MAX_PAGE_SIZE", 5)
    page = _response(200, [{"id": 10}, {"id": 11}])
    context.get_patch = patch.object(httpx.Client, "get", side_effect=[page])


@given('a bzzoiro API that returns 429 once then succeeds')
def step_429_then_success(context):
    _setup(context)
    rate_limited = _response(429, {}, headers={"Retry-After": "0"})
    success = _response(200, {"count": 1, "next": None, "previous": None, "results": [{"id": 99}]})
    context.get_patch = patch.object(httpx.Client, "get", side_effect=[rate_limited, success])
    context.sleep_patch = patch("tenacity.nap.sleep")


@given('a bzzoiro API that returns 401')
def step_401(context):
    _setup(context)
    resp = _response(401, {})
    context.get_patch = patch.object(httpx.Client, "get", side_effect=[resp])


@given('a bzzoiro API that returns 404')
def step_404(context):
    _setup(context)
    resp = _response(404, {})
    context.get_patch = patch.object(httpx.Client, "get", side_effect=[resp])


@given('a bzzoiro v2 API that returns 1 page of live events as envelope')
def step_v2_live_envelope(context):
    _setup(context)
    # Confirmed live: /api/v2/events/live/ uses an "events" key, not the
    # "results" key every other v2 list endpoint uses.
    page = _response(200, {"count": 1, "events": [{"id": 500}]})
    context.get_patch = patch.object(httpx.Client, "get", side_effect=[page])


@given('a bzzoiro v2 API that returns 1 flat page of live events')
def step_v2_flat_live_page(context):
    _setup(context)
    context.max_page_size_patch = patch.object(bzzoiro_client_module, "_MAX_PAGE_SIZE", 5)
    page = _response(200, [{"id": 501}, {"id": 502}])
    context.get_patch = patch.object(httpx.Client, "get", side_effect=[page])


@given('a bzzoiro v2 API that returns 2 full pages of odds')
def step_v2_two_full_pages(context):
    _setup(context)
    context.max_page_size_patch = patch.object(bzzoiro_client_module, "_MAX_PAGE_SIZE", 2)
    page1 = _response(200, [{"id": 1}, {"id": 2}])
    page2 = _response(200, [{"id": 3}])
    context.get_patch = patch.object(httpx.Client, "get", side_effect=[page1, page2])


@given('a bzzoiro v2 API that returns 1 partial page of odds')
def step_v2_partial_page(context):
    _setup(context)
    context.max_page_size_patch = patch.object(bzzoiro_client_module, "_MAX_PAGE_SIZE", 5)
    page = _response(200, [{"id": 1}, {"id": 2}])
    context.get_patch = patch.object(httpx.Client, "get", side_effect=[page])


@given('a bzzoiro v2 API that returns 1 page of predictions')
def step_v2_predictions_page(context):
    _setup(context)
    page = _response(200, [{"id": 1, "event": {"id": 42}}])
    context.get_patch = patch.object(httpx.Client, "get", side_effect=[page])


@given('a bzzoiro v2 API that returns 2 enveloped pages of odds')
def step_v2_enveloped_pages(context):
    _setup(context)
    page1 = _response(200, {"count": 3, "next": "https://x/?offset=2", "previous": None, "results": [{"id": 1}, {"id": 2}]})
    page2 = _response(200, {"count": 3, "next": None, "previous": "...", "results": [{"id": 3}]})
    context.get_patch = patch.object(httpx.Client, "get", side_effect=[page1, page2])


@given('a bzzoiro v2 API that returns 1 enveloped page of predictions')
def step_v2_enveloped_predictions(context):
    _setup(context)
    page = _response(200, {"count": 1, "next": None, "previous": None, "results": [{"id": 1, "event": {"id": 42}}]})
    context.get_patch = patch.object(httpx.Client, "get", side_effect=[page])


@given('a bzzoiro v2 API that returns 1 page of teams')
def step_v2_teams_page(context):
    _setup(context)
    page = _response(200, [{"id": 444, "name": "Team ABC"}])
    context.get_patch = patch.object(httpx.Client, "get", side_effect=[page])


@given('a bzzoiro v2 API that returns a squad for team 444')
def step_v2_squad_page(context):
    _setup(context)
    page = _response(200, {
        "team_id": 444,
        "count": 1,
        "players": [{"id": 1, "team_id": 444, "name": "Player One", "position": "ST", "status": "official", "club": "Club X", "club_country": "Brazil", "age": 25}]
    })
    context.get_patch = patch.object(httpx.Client, "get", side_effect=[page])


@when('I fetch events from the client')
def step_fetch_events(context):
    sleep_patch = getattr(context, "sleep_patch", None)
    with context.get_patch:
        if sleep_patch is not None:
            with sleep_patch:
                _do_fetch(context)
        else:
            _do_fetch(context)


def _do_fetch(context):
    max_page_size_patch = getattr(context, "max_page_size_patch", None)
    if max_page_size_patch is not None:
        with max_page_size_patch:
            try:
                context.result = context.client.fetch_events()
            except Exception as e:
                context.error = e
    else:
        try:
            context.result = context.client.fetch_events()
        except Exception as e:
            context.error = e


@given('a bzzoiro v2 API recording requests and returning 1 page of events')
def step_v2_events_recording_status(context):
    _setup(context)
    page = _response(200, {"count": 1, "next": None, "previous": None, "results": [{"id": 600}]})
    context.get_mock = Mock(return_value=page)
    context.get_patch = patch.object(httpx.Client, "get", context.get_mock)


@when(r'I fetch events with status "([^"]+)" from the client')
def step_fetch_events_with_status(context, status):
    with context.get_patch:
        context.result = context.client.fetch_events(status=status)


@then(r'the request was sent with status "([^"]+)"')
def step_assert_request_status(context, expected_status):
    _, kwargs = context.get_mock.call_args
    assert kwargs["params"]["status"] == expected_status, kwargs["params"]


@when('I fetch live events from the client')
def step_fetch_live(context):
    max_page_size_patch = getattr(context, "max_page_size_patch", None)
    with context.get_patch:
        if max_page_size_patch is not None:
            with max_page_size_patch:
                try:
                    context.result = context.client.fetch_live()
                except Exception as e:
                    context.error = e
        else:
            try:
                context.result = context.client.fetch_live()
            except Exception as e:
                context.error = e


@when('I fetch odds from the client')
def step_fetch_odds(context):
    max_page_size_patch = getattr(context, "max_page_size_patch", None)
    sleep_patch = getattr(context, "sleep_patch", None)
    with context.get_patch:
        if sleep_patch is not None:
            with sleep_patch:
                if max_page_size_patch is not None:
                    with max_page_size_patch:
                        _do_fetch_odds(context)
                else:
                    _do_fetch_odds(context)
        elif max_page_size_patch is not None:
            with max_page_size_patch:
                _do_fetch_odds(context)
        else:
            _do_fetch_odds(context)


def _do_fetch_odds(context):
    try:
        context.result = context.client.fetch_odds()
    except Exception as e:
        context.error = e


@when('I fetch predictions from the client')
def step_fetch_predictions(context):
    with context.get_patch:
        try:
            context.result = context.client.fetch_predictions()
        except Exception as e:
            context.error = e


@when('I fetch teams from the client')
def step_fetch_teams(context):
    with context.get_patch:
        try:
            context.result = context.client.fetch_teams()
        except Exception as e:
            context.error = e


@when('I fetch squad for team (\d+) from the client')
def step_fetch_squad(context, team_ref_id):
    with context.get_patch:
        try:
            context.result = context.client.fetch_squad(int(team_ref_id))
        except Exception as e:
            context.error = e


@then('all results across both pages are returned')
def step_all_results(context):
    ids = [r["id"] for r in context.result]
    assert ids == [1, 2, 3, 4], f"expected [1,2,3,4], got {ids}"


@then('the results from the successful response are returned')
def step_results_after_retry(context):
    assert context.error is None, f"unexpected error: {context.error}"
    assert [r["id"] for r in context.result] == [99]


@then('a BzzoiroAuthError is raised')
def step_auth_error(context):
    assert isinstance(context.error, BzzoiroAuthError), f"expected BzzoiroAuthError, got {context.error!r}"


@then('an empty list is returned')
def step_empty_list(context):
    assert context.error is None
    assert context.result == []


@then('all results from the live page are returned')
def step_live_results(context):
    assert [r["id"] for r in context.result] == [500]


@then('all odds rows across both pages are returned')
def step_all_odds_rows(context):
    assert [r["id"] for r in context.result] == [1, 2, 3], context.result


@then('only the partial page of odds is returned')
def step_partial_odds_page(context):
    assert [r["id"] for r in context.result] == [1, 2], context.result


@then('all prediction rows are returned')
def step_all_prediction_rows(context):
    assert [r["id"] for r in context.result] == [1], context.result


@then('the flat event page is returned')
def step_flat_event_page(context):
    assert context.error is None, f"unexpected error: {context.error}"
    assert [r["id"] for r in context.result] == [10, 11], context.result


@then('the flat live page is returned')
def step_flat_live_page(context):
    assert context.error is None, f"unexpected error: {context.error}"
    assert [r["id"] for r in context.result] == [501, 502], context.result


@then('all team rows are returned')
def step_all_team_rows(context):
    assert context.error is None
    assert [r["id"] for r in context.result] == [444], context.result


@then('the squad list is returned')
def step_squad_list_returned(context):
    assert context.error is None
    assert isinstance(context.result, dict)
    assert [r["id"] for r in context.result["players"]] == [1], context.result


@given('a bzzoiro API that returns 502 once then succeeds with one odds row')
def step_502_then_success(context):
    _setup(context)
    resp_502 = _response(502, {})
    resp_ok = _response(200, [{"id": 7, "updated_at": "2026-08-01T10:00:00Z"}])
    context.get_patch = patch.object(httpx.Client, "get", side_effect=[resp_502, resp_ok])
    context.sleep_patch = patch("tenacity.nap.sleep")


@given('a bzzoiro API that always raises ReadTimeout')
def step_always_timeout(context):
    _setup(context)
    context.get_patch = patch.object(
        httpx.Client, "get", side_effect=httpx.ReadTimeout("timed out", request=Mock())
    )
    context.sleep_patch = patch("tenacity.nap.sleep")


@then('only one odds row is returned without error')
def step_one_odds_row_no_error(context):
    assert context.error is None, f"unexpected error: {context.error}"
    assert len(context.result) == 1, f"expected 1 row, got {context.result}"
    assert context.result[0]["id"] == 7


@then('a BzzoiroTransientError is raised')
def step_transient_error(context):
    assert isinstance(context.error, BzzoiroTransientError), (
        f"expected BzzoiroTransientError, got {context.error!r}"
    )


@given(r'a bzzoiro API that returns an odds comparison payload for event (\d+)')
def step_odds_comparison_payload(context, event_id):
    _setup(context)
    payload = {
        "event_id": int(event_id), "bookmakers_count": 3, "total_odds": 10,
        "markets": {"1x2": {"HOME": {"best_odds": 2.1, "best_bookmaker_slug": "bet365", "bookmakers": {}}}},
    }
    resp = _response(200, payload)
    context.get_patch = patch.object(httpx.Client, "get", side_effect=[resp])


@when(r'I fetch odds comparison for event (\d+) from the client')
def step_fetch_odds_comparison(context, event_id):
    with context.get_patch:
        try:
            context.result = context.client.fetch_odds_comparison(int(event_id))
        except Exception as e:
            context.error = e


@when(r'I fetch polymarket for event (\d+) from the client')
def step_fetch_polymarket(context, event_id):
    with context.get_patch:
        try:
            context.result = context.client.fetch_polymarket(int(event_id))
        except Exception as e:
            context.error = e


@then('the odds comparison payload is returned')
def step_assert_odds_comparison_payload(context):
    assert context.error is None, f"unexpected error: {context.error}"
    assert context.result["bookmakers_count"] == 3, context.result


@then('None is returned by the client')
def step_assert_none_returned(context):
    assert context.error is None, f"unexpected error: {context.error}"
    assert context.result is None, context.result


@given(r'a bzzoiro API that returns a lineups payload for event (\d+)')
def step_lineups_payload(context, event_id):
    _setup(context)
    payload = {
        "event_id": int(event_id), "lineup_status": "predicted", "beta": True,
        "lineups": {"home": {"confidence": 0.8}, "away": {"confidence": 0.7}},
    }
    resp = _response(200, payload)
    context.get_patch = patch.object(httpx.Client, "get", side_effect=[resp])


@when(r'I fetch lineups for event (\d+) from the client')
def step_fetch_lineups(context, event_id):
    with context.get_patch:
        try:
            context.result = context.client.fetch_lineups(int(event_id))
        except Exception as e:
            context.error = e


@then('the lineups payload is returned')
def step_assert_lineups_payload(context):
    assert context.error is None, f"unexpected error: {context.error}"
    assert context.result["lineup_status"] == "predicted", context.result


@given(r'a bzzoiro API that returns a h2h payload for event (\d+)')
def step_h2h_payload(context, event_id):
    _setup(context)
    payload = {"total_matches": 0, "home_wins": 0, "draws": 0, "away_wins": 0}
    resp = _response(200, payload)
    context.get_patch = patch.object(httpx.Client, "get", side_effect=[resp])


@when(r'I fetch h2h for event (\d+) from the client')
def step_fetch_h2h(context, event_id):
    with context.get_patch:
        try:
            context.result = context.client.fetch_h2h(int(event_id))
        except Exception as e:
            context.error = e


@then('the h2h payload is returned')
def step_assert_h2h_payload(context):
    assert context.error is None, f"unexpected error: {context.error}"
    assert context.result["total_matches"] == 0, context.result


@given('a bzzoiro v2 API that returns 1 page of best odds')
def step_odds_best_payload(context):
    _setup(context)
    page = _response(200, {
        "count": 1,
        "results": [{
            "event_id": 46387, "market": "1x2",
            "best_odds": [{"outcome": "HOME", "decimal_odds": 3.23, "bookmaker_slug": "pinnacle"}],
        }],
    })
    context.get_patch = patch.object(httpx.Client, "get", side_effect=[page])


@when('I fetch odds best from the client')
def step_fetch_odds_best(context):
    with context.get_patch:
        try:
            context.result = context.client.fetch_odds_best()
        except Exception as e:
            context.error = e


@then('the odds best rows are returned')
def step_assert_odds_best_rows(context):
    assert context.error is None, f"unexpected error: {context.error}"
    assert len(context.result) == 1, context.result
    assert context.result[0]["event_id"] == 46387, context.result


@given(r'a bzzoiro API that returns a standings payload for league (\d+)')
def step_standings_payload(context, league_id):
    _setup(context)
    payload = {"league_id": int(league_id), "standings": [{"team_id": 1, "position": 1}]}
    resp = _response(200, payload)
    context.get_patch = patch.object(httpx.Client, "get", side_effect=[resp])


@when(r'I fetch standings for league (\d+) from the client')
def step_fetch_standings(context, league_id):
    with context.get_patch:
        try:
            context.result = context.client.fetch_standings(int(league_id))
        except Exception as e:
            context.error = e


@then('the standings payload is returned')
def step_assert_standings_payload(context):
    assert context.error is None, f"unexpected error: {context.error}"
    assert len(context.result["standings"]) == 1, context.result


@given(r'a bzzoiro API that returns a venue payload for venue (\d+)')
def step_venue_payload(context, venue_id):
    _setup(context)
    payload = {
        "id": int(venue_id), "name": "Estadio Municipal de Butarque", "city": "Leganes",
        "country": "Spain", "capacity": 12454,
    }
    resp = _response(200, payload)
    context.get_patch = patch.object(httpx.Client, "get", side_effect=[resp])


@when(r'I fetch venue (\d+) from the client')
def step_fetch_venue(context, venue_id):
    with context.get_patch:
        try:
            context.result = context.client.fetch_venue(int(venue_id))
        except Exception as e:
            context.error = e


@then('the venue payload is returned')
def step_assert_venue_payload(context):
    assert context.error is None, f"unexpected error: {context.error}"
    assert context.result["name"] == "Estadio Municipal de Butarque", context.result


@given(r'a bzzoiro API that returns a referee payload for referee (\d+)')
def step_referee_payload(context, referee_id):
    _setup(context)
    payload = {"id": int(referee_id), "name": "Alireza Faghani", "country": "Australia"}
    resp = _response(200, payload)
    context.get_patch = patch.object(httpx.Client, "get", side_effect=[resp])


@when(r'I fetch referee (\d+) from the client')
def step_fetch_referee(context, referee_id):
    with context.get_patch:
        try:
            context.result = context.client.fetch_referee(int(referee_id))
        except Exception as e:
            context.error = e


@then('the referee payload is returned')
def step_assert_referee_payload(context):
    assert context.error is None, f"unexpected error: {context.error}"
    assert context.result["name"] == "Alireza Faghani", context.result


@given(r'a bzzoiro API that returns a player stats payload for event (\d+)')
def step_player_stats_payload(context, event_id):
    _setup(context)
    payload = {
        "event_id": int(event_id), "count": 1,
        "player_stats": [{"id": 1, "player_id": 10, "team_id": 1, "minutes_played": 90}],
    }
    resp = _response(200, payload)
    context.get_patch = patch.object(httpx.Client, "get", side_effect=[resp])


@when(r'I fetch player stats for event (\d+) from the client')
def step_fetch_player_stats(context, event_id):
    with context.get_patch:
        try:
            context.result = context.client.fetch_player_stats(int(event_id))
        except Exception as e:
            context.error = e


@then('the player stats payload is returned')
def step_assert_player_stats_payload(context):
    assert context.error is None, f"unexpected error: {context.error}"
    assert context.result["count"] == 1, context.result


@given(r'a bzzoiro API that returns an incidents payload for event (\d+)')
def step_incidents_payload(context, event_id):
    _setup(context)
    payload = {
        "event_id": int(event_id),
        "incidents": [{"type": "period", "text": "FT", "minute": 90}],
    }
    resp = _response(200, payload)
    context.get_patch = patch.object(httpx.Client, "get", side_effect=[resp])


@when(r'I fetch incidents for event (\d+) from the client')
def step_fetch_incidents(context, event_id):
    with context.get_patch:
        try:
            context.result = context.client.fetch_incidents(int(event_id))
        except Exception as e:
            context.error = e


@then('the incidents payload is returned')
def step_assert_incidents_payload(context):
    assert context.error is None, f"unexpected error: {context.error}"
    assert len(context.result["incidents"]) == 1, context.result
