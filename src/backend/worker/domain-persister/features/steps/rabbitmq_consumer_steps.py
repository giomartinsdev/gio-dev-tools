from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

from behave import given, then, use_step_matcher, when

import src.infrastructure.rabbitmq_consumer as consumer_module
from shared.events import EventMeta, MatchStatus, MatchStatusChanged, RawFeedReceived

use_step_matcher("re")


class _FakeMessage:
    def __init__(self, body: bytes):
        self.body = body
        self.ack = AsyncMock()
        self.nack = AsyncMock()


class _FakeQueueIterator:
    def __init__(self, messages):
        self._messages = list(messages)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    def __aiter__(self):
        return self

    async def __anext__(self):
        if not self._messages:
            raise StopAsyncIteration
        return self._messages.pop(0)


class _FakeQueue:
    def __init__(self, messages):
        self._iterator = _FakeQueueIterator(messages)

    def iterator(self):
        return self._iterator


class _FakeConnection:
    def __init__(self, channel):
        self._channel = channel

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def channel(self):
        return self._channel


def _raw_envelope_json(good: bool) -> bytes:
    if not good:
        return b"not-json-at-all"
    envelope = RawFeedReceived(
        meta=EventMeta(occurred_at=datetime.now(timezone.utc), producer="acl.bzzoiro", correlation_id=uuid4()),
        source="bzzoiro", feed_type="fixtures", provider_ref="1", payload={"a": 1},
    )
    return envelope.model_dump_json().encode()


def _domain_event_json(good: bool) -> bytes:
    if not good:
        return b"not-json-at-all"
    event = MatchStatusChanged(
        meta=EventMeta(occurred_at=datetime.now(timezone.utc), producer="acl.bzzoiro", correlation_id=uuid4()),
        match_id=uuid4(), status=MatchStatus.LIVE, minute=5,
    )
    return event.model_dump_json().encode()


def _run_one_cycle(coro_factory, connect_side_effect):
    async def scenario():
        with patch.object(consumer_module.aio_pika, "connect_robust", AsyncMock(side_effect=connect_side_effect)), \
             patch.object(consumer_module, "declare_topology", AsyncMock()):
            try:
                await coro_factory()
            except asyncio.CancelledError:
                pass

    asyncio.run(scenario())


@given('a fake broker with one good raw message and one poison raw message')
def step_broker_raw_messages(context):
    context.event_store = Mock()
    channel = Mock()
    channel.set_qos = AsyncMock()
    good = _FakeMessage(_raw_envelope_json(True))
    poison = _FakeMessage(_raw_envelope_json(False))
    queue = _FakeQueue([good, poison])
    channel.get_queue = AsyncMock(return_value=queue)
    context.connection = _FakeConnection(channel)
    context.good_message = good
    context.poison_message = poison


@given('a fake broker with one good domain message and one poison domain message')
def step_broker_domain_messages(context):
    context.projector = Mock()

    def _handle(body):
        if body == b"not-json-at-all":
            raise ValueError("poison message")

    context.projector.handle.side_effect = _handle
    channel = Mock()
    channel.set_qos = AsyncMock()
    good = _FakeMessage(_domain_event_json(True))
    poison = _FakeMessage(_domain_event_json(False))
    queue = _FakeQueue([good, poison])
    channel.get_queue = AsyncMock(return_value=queue)
    context.connection = _FakeConnection(channel)
    context.good_message = good
    context.poison_message = poison


@given('a fake broker that fails to connect once')
def step_broker_fails_once(context):
    context.event_store = Mock()


@when('the archive-raw consumer runs one connection cycle')
def step_run_archive_raw(context):
    if hasattr(context, "connection"):
        _run_one_cycle(
            lambda: consumer_module._consume_archive_raw("amqp://fake", context.event_store),
            [context.connection, asyncio.CancelledError],
        )
    else:
        with patch.object(consumer_module.asyncio, "sleep", AsyncMock()) as fake_sleep:
            _run_one_cycle(
                lambda: consumer_module._consume_archive_raw("amqp://fake", context.event_store),
                [RuntimeError("connection refused"), asyncio.CancelledError],
            )
            context.fake_sleep = fake_sleep


@when('the persister consumer runs one connection cycle')
def step_run_persister(context):
    _run_one_cycle(
        lambda: consumer_module._consume_persister("amqp://fake", context.projector),
        [context.connection, asyncio.CancelledError],
    )


@then('the good message was appended and acked')
def step_assert_appended_acked(context):
    context.event_store.append.assert_called_once()
    kwargs = context.event_store.append.call_args.kwargs
    assert kwargs["event_type"] == "raw.feed_received"


@then('the poison message was nacked without requeue')
def step_assert_nacked(context):
    context.poison_message.nack.assert_awaited_once_with(requeue=False)


@then('the good message was projected and acked')
def step_assert_projected(context):
    context.projector.handle.assert_any_call(context.good_message.body)
    context.good_message.ack.assert_awaited_once()


@then('the connection was retried after the reconnect delay')
def step_assert_retried(context):
    context.fake_sleep.assert_awaited_with(consumer_module.RECONNECT_DELAY)


@given('a fake broker with one good raw message and one good domain message')
def step_broker_both(context):
    context.event_store = Mock()
    context.projector = Mock()
    context.raw_calls = []
    context.persister_calls = []


@when('run_consumers executes one cycle of both loops')
def step_run_both(context):
    async def fake_archive_raw(uri, event_store):
        context.raw_calls.append((uri, event_store))

    async def fake_persister(uri, projector):
        context.persister_calls.append((uri, projector))

    async def scenario():
        with patch.object(consumer_module, "_consume_archive_raw", fake_archive_raw), \
             patch.object(consumer_module, "_consume_persister", fake_persister):
            await consumer_module.run_consumers("amqp://fake", context.event_store, context.projector)

    asyncio.run(scenario())


@then('both queues were consumed')
def step_assert_both_consumed(context):
    assert context.raw_calls == [("amqp://fake", context.event_store)]
    assert context.persister_calls == [("amqp://fake", context.projector)]
