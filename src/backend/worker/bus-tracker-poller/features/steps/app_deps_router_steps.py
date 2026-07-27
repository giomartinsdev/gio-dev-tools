from __future__ import annotations

import asyncio
import threading
from types import SimpleNamespace

from behave import given, then, use_step_matcher, when
from fastapi import HTTPException

from app.deps import _ready, get_client, get_publisher, get_tracked_lines
from app.router import poll

use_step_matcher("re")


def _fake_request(**state_kwargs):
    state = SimpleNamespace(**state_kwargs)
    return SimpleNamespace(app=SimpleNamespace(state=state))


@given('app state with init done and no error')
def step_state_ok(context):
    init_done = threading.Event()
    init_done.set()
    context.request = _fake_request(
        _init_done=init_done, _init_error=None,
        client="the-client", tracked_lines="the-tracked-lines", publisher="the-publisher",
    )
    context.error = None


@given('app state with init done and an init error')
def step_state_error(context):
    init_done = threading.Event()
    init_done.set()
    context.request = _fake_request(_init_done=init_done, _init_error=RuntimeError("boom"), publisher=None)
    context.error = None


@given('app state with init done, no error, but rabbitmq not connected')
def step_state_not_connected(context):
    init_done = threading.Event()
    init_done.set()
    context.request = _fake_request(_init_done=init_done, _init_error=None, publisher=None)
    context.error = None


@when('I call _ready')
def step_call_ready(context):
    _ready(context.request)


@when('I call _ready expecting an error')
def step_call_ready_expecting_error(context):
    try:
        _ready(context.request)
    except HTTPException as e:
        context.error = e


@when('I call the dependency getters')
def step_call_getters(context):
    context.got_client = get_client(context.request)
    context.got_tracked_lines = get_tracked_lines(context.request)
    context.got_publisher = get_publisher(context.request)


@then('no exception is raised')
def step_no_exception(context):
    assert context.error is None


@then('a 503 HTTPException is raised')
def step_503(context):
    assert isinstance(context.error, HTTPException), context.error
    assert context.error.status_code == 503, context.error.status_code


@then('each getter returns the matching state object')
def step_getters_match(context):
    assert context.got_client == "the-client"
    assert context.got_tracked_lines == "the-tracked-lines"
    assert context.got_publisher == "the-publisher"


class _FakePublisher:
    def __init__(self):
        self.domain_events = []

    async def publish_domain_event(self, event):
        self.domain_events.append(event)


class _FakeClient:
    def __init__(self, rows):
        self._rows = rows

    def fetch_sppo_positions(self, data_inicial, data_final):
        return self._rows

    def fetch_brt_positions(self):
        return []

    def fetch_vehicle_colors(self):
        return {}


class _FakeTrackedLines:
    def __init__(self, active_codes):
        self._active_codes = set(active_codes)

    def find_active_line_codes(self, mode):
        return self._active_codes if mode == "sppo" else set()


class _RaisingTrackedLines:
    def find_active_line_codes(self, mode):
        raise RuntimeError("db down")


@given('fake poll dependencies with 1 position for an active line')
def step_fake_deps_one_position(context):
    context.client = _FakeClient([{
        "ordem": "A1", "linha": "483", "latitude": "-22,9", "longitude": "-43,2",
        "velocidade": "30", "datahora": "1700000000000",
    }])
    context.tracked_lines = _FakeTrackedLines(["483"])
    context.publisher = _FakePublisher()
    context.error = None
    context.endpoint_result = None


@given('a poll handler that raises an error')
def step_raising_deps(context):
    context.client = _FakeClient([])
    context.tracked_lines = _RaisingTrackedLines()
    context.publisher = _FakePublisher()
    context.error = None


@when('I call the poll endpoint')
def step_call_poll(context):
    context.endpoint_result = asyncio.run(
        poll(client=context.client, tracked_lines=context.tracked_lines, publisher=context.publisher)
    )


@when('I call the poll endpoint expecting an error')
def step_call_poll_error(context):
    try:
        asyncio.run(
            poll(client=context.client, tracked_lines=context.tracked_lines, publisher=context.publisher)
        )
    except HTTPException as e:
        context.error = e


@then(r'the endpoint returns polled count (\d+)')
def step_assert_polled_count(context, count):
    assert context.endpoint_result["polled"] == int(count), context.endpoint_result


@then('a 500 HTTPException is raised')
def step_500(context):
    assert isinstance(context.error, HTTPException), context.error
    assert context.error.status_code == 500, context.error.status_code
