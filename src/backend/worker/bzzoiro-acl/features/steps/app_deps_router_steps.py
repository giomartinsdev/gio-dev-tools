from __future__ import annotations

import asyncio
import threading
from types import SimpleNamespace

from behave import given, then, use_step_matcher, when
from fastapi import HTTPException

from app.deps import _ready, get_client, get_publisher, get_translator
from app.router import (
    poll_fixtures,
    poll_live,
    poll_odds,
    poll_odds_comparison,
    poll_predictions,
    poll_teams,
    resync,
)

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
        client="the-client", translator="the-translator", publisher="the-publisher",
    )
    context.error = None


@given('app state with init done and an init error')
def step_state_error(context):
    init_done = threading.Event()
    init_done.set()
    context.request = _fake_request(_init_done=init_done, _init_error=RuntimeError("boom"), publisher=None)
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
    context.got_translator = get_translator(context.request)
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
    assert context.got_translator == "the-translator"
    assert context.got_publisher == "the-publisher"


class _FakePublisher:
    def __init__(self):
        self.raw_calls = []
        self.domain_events = []
        self.insights = []

    async def publish_raw(self, feed_type, provider_ref, payload, correlation_id=None):
        self.raw_calls.append((feed_type, provider_ref, payload))

    async def publish_domain_event(self, event):
        self.domain_events.append(event)

    async def publish_insight(self, event):
        self.insights.append(event)


class _FakeClient:
    def __init__(self, payloads):
        self._payloads = payloads

    def fetch_events(self, date_from=None, date_to=None, status=None):
        return self._payloads

    def fetch_live(self):
        return self._payloads

    def fetch_odds(self, updated_after=None):
        return []

    def fetch_odds_page(self, offset=0, limit=200, updated_after=None):
        return [], False

    def fetch_predictions(self, status="upcoming"):
        return []

    def fetch_odds_comparison(self, event_ref_id):
        return None

    def fetch_polymarket(self, event_ref_id):
        return None

    def fetch_teams(self) -> list[dict]:
        return []

    def fetch_squad(self, team_ref_id: int) -> list[dict]:
        return []


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


class _RaisingClient:
    def fetch_events(self, date_from=None, date_to=None, status=None):
        raise RuntimeError("upstream down")

    def fetch_live(self):
        raise RuntimeError("upstream down")

    def fetch_odds(self, updated_after=None):
        raise RuntimeError("upstream down")

    def fetch_odds_page(self, offset=0, limit=200, updated_after=None):
        raise RuntimeError("upstream down")

    def fetch_predictions(self, status="upcoming"):
        raise RuntimeError("upstream down")

    def fetch_odds_comparison(self, event_ref_id):
        raise RuntimeError("upstream down")

    def fetch_polymarket(self, event_ref_id):
        raise RuntimeError("upstream down")

    def fetch_teams(self) -> list[dict]:
        raise RuntimeError("upstream down")

    def fetch_squad(self, team_ref_id: int) -> list[dict]:
        raise RuntimeError("upstream down")


_SAMPLE_PAYLOAD = {
    "id": "555",
    "status": {"name": "live"},
    "home": {"id": "10"},
    "away": {"id": "20"},
    "league": {"id": "1"},
    "score": {"home": 1, "away": 1},
}


@given('fake poll dependencies with 1 fixture payload')
def step_fake_deps_fixture(context):
    from src.domain.repository import IdentityRepository
    from src.infrastructure.translator import BzzoiroTranslator
    from uuid import uuid4

    class _Ident(IdentityRepository):
        def get_or_create(self, provider, provider_ref, entity_type):
            return uuid4()

    context.client = _FakeClient([_SAMPLE_PAYLOAD])
    context.translator = BzzoiroTranslator(_Ident())
    context.publisher = _FakePublisher()
    context.checkpoints = _FakeCheckpointRepository()
    context.error = None
    context.endpoint_result = None


@given('fake poll dependencies with 1 live payload')
def step_fake_deps_live(context):
    step_fake_deps_fixture(context)


@given('a poll handler that raises an error')
def step_raising_client(context):
    context.client = _RaisingClient()
    from src.infrastructure.translator import BzzoiroTranslator
    from src.domain.repository import IdentityRepository
    from uuid import uuid4

    class _Ident(IdentityRepository):
        def get_or_create(self, provider, provider_ref, entity_type):
            return uuid4()

    context.translator = BzzoiroTranslator(_Ident())
    context.publisher = _FakePublisher()
    context.checkpoints = _FakeCheckpointRepository()
    context.error = None


@when('I call the poll_fixtures endpoint')
def step_call_poll_fixtures(context):
    context.endpoint_result = asyncio.run(
        poll_fixtures(client=context.client, translator=context.translator, publisher=context.publisher)
    )


@when('I call the poll_fixtures endpoint expecting an error')
def step_call_poll_fixtures_error(context):
    try:
        asyncio.run(
            poll_fixtures(client=context.client, translator=context.translator, publisher=context.publisher)
        )
    except HTTPException as e:
        context.error = e


@when('I call the poll_live endpoint')
def step_call_poll_live(context):
    context.endpoint_result = asyncio.run(
        poll_live(client=context.client, translator=context.translator, publisher=context.publisher)
    )


@when('I call the poll_odds endpoint')
def step_call_poll_odds(context):
    context.endpoint_result = asyncio.run(
        poll_odds(
            client=context.client, translator=context.translator,
            publisher=context.publisher, checkpoints=context.checkpoints,
        )
    )


@when('I call the poll_odds endpoint expecting an error')
def step_call_poll_odds_error(context):
    try:
        asyncio.run(
            poll_odds(
                client=context.client, translator=context.translator,
                publisher=context.publisher, checkpoints=context.checkpoints,
            )
        )
    except HTTPException as e:
        context.error = e


@when('I call the poll_odds_comparison endpoint')
def step_call_poll_odds_comparison(context):
    context.endpoint_result = asyncio.run(
        poll_odds_comparison(client=context.client, translator=context.translator, publisher=context.publisher)
    )


@when('I call the poll_odds_comparison endpoint expecting an error')
def step_call_poll_odds_comparison_error(context):
    try:
        asyncio.run(
            poll_odds_comparison(client=context.client, translator=context.translator, publisher=context.publisher)
        )
    except HTTPException as e:
        context.error = e


@when('I call the poll_teams endpoint')
def step_call_poll_teams(context):
    context.endpoint_result = asyncio.run(
        poll_teams(
            client=context.client, translator=context.translator,
            publisher=context.publisher, checkpoints=context.checkpoints,
        )
    )


@when('I call the poll_teams endpoint expecting an error')
def step_call_poll_teams_error(context):
    try:
        asyncio.run(
            poll_teams(
                client=context.client, translator=context.translator,
                publisher=context.publisher, checkpoints=context.checkpoints,
            )
        )
    except HTTPException as e:
        context.error = e


@when('I call the resync endpoint')
def step_call_resync(context):
    context.endpoint_result = asyncio.run(
        resync(
            client=context.client, translator=context.translator,
            publisher=context.publisher, checkpoints=context.checkpoints,
        )
    )


@when('I call the resync endpoint expecting an error')
def step_call_resync_error(context):
    try:
        asyncio.run(
            resync(
                client=context.client, translator=context.translator,
                publisher=context.publisher, checkpoints=context.checkpoints,
            )
        )
    except HTTPException as e:
        context.error = e


@when('I call the poll_predictions endpoint')
def step_call_poll_predictions(context):
    context.endpoint_result = asyncio.run(
        poll_predictions(client=context.client, translator=context.translator, publisher=context.publisher)
    )


@when('I call the poll_predictions endpoint expecting an error')
def step_call_poll_predictions_error(context):
    try:
        asyncio.run(
            poll_predictions(client=context.client, translator=context.translator, publisher=context.publisher)
        )
    except HTTPException as e:
        context.error = e


@then(r'the endpoint returns polled count (\d+)')
def step_assert_polled_count(context, count):
    assert context.endpoint_result["polled"] == int(count), context.endpoint_result


@then('the resync endpoint reports all six feeds')
def step_assert_resync_feeds(context):
    resynced = context.endpoint_result["resynced"]
    assert set(resynced.keys()) == {
        "fixtures", "live", "odds", "odds_comparison", "predictions", "teams",
    }, resynced


@then('a 500 HTTPException is raised')
def step_500(context):
    assert isinstance(context.error, HTTPException), context.error
    assert context.error.status_code == 500, context.error.status_code
