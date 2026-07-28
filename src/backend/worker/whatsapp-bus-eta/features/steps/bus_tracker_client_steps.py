from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from behave import given, then, use_step_matcher, when

from src.infrastructure.bus_tracker_client import BusTrackerClient

use_step_matcher("re")


def _make_client_cm(get_responses=None, post_response=None):
    client = MagicMock()
    if get_responses is not None:
        client.get = MagicMock(side_effect=get_responses)
    client.post = MagicMock(return_value=post_response or MagicMock())
    cm = MagicMock()
    cm.__enter__ = MagicMock(return_value=client)
    cm.__exit__ = MagicMock(return_value=False)
    return cm, client


def _response(payload):
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.json = MagicMock(return_value=payload)
    return resp


@given(r'the bus-tracker api already tracks mode "([^"]+)" line "([^"]+)"')
def step_line_exists(context, mode, line_code):
    lines_resp = _response([{"mode": mode, "line_code": line_code}])
    cm, client = _make_client_cm(get_responses=[lines_resp])
    context.client_cm = cm
    context.client = client


@given("the bus-tracker api tracks no lines")
def step_no_lines(context):
    lines_resp = _response([])
    cm, client = _make_client_cm(get_responses=[lines_resp])
    context.client_cm = cm
    context.client = client


@given(r'the bus-tracker api returns positions (\[.*\]) for mode "([^"]+)" line "([^"]+)"')
def step_positions(context, payload, mode, line_code):
    resp = _response(json.loads(payload))
    cm, client = _make_client_cm(get_responses=[resp])
    context.client_cm = cm
    context.client = client


@given(r'the bus-tracker api returns stops (\[.*\]) for mode "([^"]+)" line "([^"]+)"')
def step_stops(context, payload, mode, line_code):
    resp = _response(json.loads(payload))
    cm, client = _make_client_cm(get_responses=[resp])
    context.client_cm = cm
    context.client = client


@when(r'I ensure line "([^"]+)" mode "([^"]+)" is tracked')
def step_ensure(context, line_code, mode):
    bus_tracker = BusTrackerClient()
    with patch("httpx.Client", return_value=context.client_cm):
        bus_tracker.ensure_tracked_line(mode, line_code)


@when(r'I fetch latest positions for mode "([^"]+)" line "([^"]+)"')
def step_fetch_positions(context, mode, line_code):
    bus_tracker = BusTrackerClient()
    with patch("httpx.Client", return_value=context.client_cm):
        context.result = bus_tracker.find_latest_positions(mode, line_code)


@when(r'I fetch stops for mode "([^"]+)" line "([^"]+)"')
def step_fetch_stops(context, mode, line_code):
    bus_tracker = BusTrackerClient()
    with patch("httpx.Client", return_value=context.client_cm):
        context.result = bus_tracker.find_stops(mode, line_code)


@then("no POST to /lines was made")
def step_no_post(context):
    context.client.post.assert_not_called()


@then(r'a POST to /lines was made for line "([^"]+)" mode "([^"]+)"')
def step_post_made(context, line_code, mode):
    context.client.post.assert_called_once()
    args, kwargs = context.client.post.call_args
    assert kwargs["json"]["line_code"] == line_code
    assert kwargs["json"]["mode"] == mode


@then(r"the positions result is (\[.*\])")
def step_positions_result(context, payload):
    assert context.result == json.loads(payload)


@then(r"the stops result is (\[.*\])")
def step_stops_result(context, payload):
    assert context.result == json.loads(payload)
