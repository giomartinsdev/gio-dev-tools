from __future__ import annotations

import asyncio
from uuid import UUID, uuid4

from behave import given, then, use_step_matcher, when

from src.application.commands.poll_fixtures import PollFixturesCommand, PollFixturesHandler
from src.application.commands.poll_live import PollLiveCommand, PollLiveHandler
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

    def fetch_events(self, date_from=None, date_to=None, status=None):
        return self.events_payloads

    def fetch_live(self):
        return self.live_payloads


class _FakePublisher:
    def __init__(self):
        self.raw_calls: list[tuple] = []
        self.domain_events: list = []

    async def publish_raw(self, feed_type, provider_ref, payload, correlation_id=None):
        self.raw_calls.append((feed_type, provider_ref, payload, correlation_id))

    async def publish_domain_event(self, event):
        self.domain_events.append(event)


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


@when('I run the fixtures poll handler')
def step_run_fixtures(context):
    handler = PollFixturesHandler(context.client, context.translator, context.publisher)
    context.polled_count = asyncio.run(handler.handle(PollFixturesCommand()))


@when('I run the live poll handler')
def step_run_live(context):
    handler = PollLiveHandler(context.client, context.translator, context.publisher)
    context.polled_count = asyncio.run(handler.handle(PollLiveCommand()))


@then(r'(\d+) events? (?:was|were) polled')
def step_assert_count(context, expected):
    assert context.polled_count == int(expected), f"expected {expected}, got {context.polled_count}"


@then('the publisher recorded a raw publish and at least one domain event publish')
def step_assert_published(context):
    assert len(context.publisher.raw_calls) == 1, context.publisher.raw_calls
    assert len(context.publisher.domain_events) >= 1, context.publisher.domain_events


@then('the publisher recorded no raw publish')
def step_assert_no_raw(context):
    assert context.publisher.raw_calls == []
