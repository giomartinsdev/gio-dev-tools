from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, Mock, patch

from behave import given, then, use_step_matcher, when

import src.infrastructure.trigger_queue as trigger_queue_module
import src.infrastructure.value_bets_client as value_bets_client_module
import src.infrastructure.whatsapp_publisher as whatsapp_publisher_module
from src.infrastructure.trigger_queue import TriggerPublisher, consume_triggers
from src.infrastructure.value_bets_client import ValueBetsClient
from src.infrastructure.whatsapp_publisher import WhatsAppPublisher

use_step_matcher("re")


def _fake_channel(context):
    channel = Mock()
    channel.declare_queue = AsyncMock()

    async def _publish(message, routing_key):
        context.published.append((routing_key, json.loads(message.body.decode())))

    channel.default_exchange = Mock()
    channel.default_exchange.publish = AsyncMock(side_effect=_publish)
    return channel


@given('a fresh whatsapp publisher')
def step_fresh_publisher(context):
    context.published = []
    channel = _fake_channel(context)
    connection = Mock()
    connection.channel = AsyncMock(return_value=channel)
    connection.close = AsyncMock()
    context.connect_patch = patch.object(
        whatsapp_publisher_module.aio_pika, "connect_robust", AsyncMock(return_value=connection),
    )
    context.publisher = WhatsAppPublisher("amqp://fake")


@given('a fresh trigger publisher')
def step_fresh_trigger_publisher(context):
    context.published = []
    channel = _fake_channel(context)
    connection = Mock()
    connection.channel = AsyncMock(return_value=channel)
    connection.close = AsyncMock()
    context.connect_patch = patch.object(
        trigger_queue_module.aio_pika, "connect_robust", AsyncMock(return_value=connection),
    )
    context.trigger_publisher = TriggerPublisher("amqp://fake")


@when(r'I publish "([^"]+)" to "([^"]+)"')
def step_publish(context, text, number):
    with context.connect_patch:
        asyncio.run(context.publisher.publish(number, text))


@when(r'I publish "([^"]+)" to "([^"]+)" with instance "([^"]+)"')
def step_publish_with_instance(context, text, number, instance):
    with context.connect_patch:
        asyncio.run(context.publisher.publish(number, text, instance))


@when(r'I publish a trigger with reason "([^"]+)"')
def step_publish_trigger(context, reason):
    with context.connect_patch:
        asyncio.run(context.trigger_publisher.publish(reason))


@then(r'a message was published to the whatsapp-send queue with number "([^"]+)" and text "([^"]+)"')
def step_assert_whatsapp_published(context, number, text):
    assert context.published, "no message was published"
    routing_key, payload = context.published[0]
    assert routing_key == "whatsapp-send", routing_key
    assert payload["number"] == number, payload
    assert payload["text"] == text, payload


@then('the published whatsapp message includes the instance "([^"]+)"')
def step_assert_instance(context, instance):
    _, payload = context.published[0]
    assert payload.get("instance") == instance, payload


@then(r'a message was published to the value-bets-report-trigger queue with reason "([^"]+)"')
def step_assert_trigger_published(context, reason):
    assert context.published, "no message was published"
    routing_key, payload = context.published[0]
    assert routing_key == "value-bets-report-trigger", routing_key
    assert payload["reason"] == reason, payload
    assert "triggered_at" in payload


@given('a value bets client returning a full page then a short page')
def step_value_bets_client_pages(context):
    full_page = [{"match_id": f"m{i}"} for i in range(50)]
    short_page = [{"match_id": "m50"}]

    responses = [Mock(), Mock()]
    responses[0].json.return_value = full_page
    responses[0].raise_for_status = Mock()
    responses[1].json.return_value = short_page
    responses[1].raise_for_status = Mock()

    fake_http_client = AsyncMock()
    fake_http_client.get = AsyncMock(side_effect=responses)
    fake_http_client.__aenter__ = AsyncMock(return_value=fake_http_client)
    fake_http_client.__aexit__ = AsyncMock(return_value=False)

    context.expected_total = len(full_page) + len(short_page)
    context.client_patch = patch.object(
        value_bets_client_module.httpx, "AsyncClient", Mock(return_value=fake_http_client),
    )
    context.value_bets_client = ValueBetsClient()


@when('I fetch value bets')
def step_fetch_value_bets(context):
    with context.client_patch:
        context.result = asyncio.run(context.value_bets_client.fetch())


@then('all pages were combined into the result')
def step_assert_combined(context):
    assert len(context.result) == context.expected_total, len(context.result)


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


@given('a fake broker with one good trigger message and one poison trigger message')
def step_broker_trigger_messages(context):
    context.on_trigger_calls = []

    async def on_trigger():
        context.on_trigger_calls.append(1)
        if len(context.on_trigger_calls) > 1:
            raise ValueError("poison")

    context.on_trigger = on_trigger

    channel = Mock()
    channel.set_qos = AsyncMock()
    channel.declare_queue = AsyncMock()
    good = _FakeMessage(b'{"reason": "scheduled"}')
    poison = _FakeMessage(b'{"reason": "scheduled"}')
    queue = _FakeQueue([good, poison])
    channel.declare_queue.return_value = queue
    context.connection = _FakeConnection(channel)
    context.good_message = good
    context.poison_message = poison


@when('the trigger consumer runs one connection cycle')
def step_run_trigger_consumer(context):
    async def scenario():
        with patch.object(
            trigger_queue_module.aio_pika, "connect_robust",
            AsyncMock(side_effect=[context.connection, asyncio.CancelledError]),
        ):
            try:
                await consume_triggers("amqp://fake", context.on_trigger)
            except asyncio.CancelledError:
                pass

    asyncio.run(scenario())


@then('the on_trigger callback ran once and the good message was acked')
def step_assert_trigger_ran(context):
    assert len(context.on_trigger_calls) >= 1
    context.good_message.ack.assert_awaited_once()


@then('the poison message was nacked without requeue')
def step_assert_poison_nacked(context):
    context.poison_message.nack.assert_awaited_once_with(requeue=False)
