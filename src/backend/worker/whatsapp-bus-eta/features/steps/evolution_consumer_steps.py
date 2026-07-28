from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, Mock, patch

from behave import given, then, use_step_matcher, when

import src.infrastructure.evolution_consumer as consumer_module

use_step_matcher("re")


class _FakeMessage:
    def __init__(self, body: bytes):
        self.body = body
        self.ack = AsyncMock()
        self.nack = AsyncMock()

    def process(self, requeue=False):
        return self

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if exc is None:
            await self.ack()
        else:
            await self.nack(requeue=requeue)
        return True


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
        self.bind = AsyncMock()

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


def _good_body() -> bytes:
    return json.dumps({
        "data": {"key": {"remoteJid": "5511999@s.whatsapp.net", "fromMe": False}, "message": {"conversation": "483"}},
    }).encode()


def _run_one_cycle(coro_factory, connect_side_effect):
    async def scenario():
        with patch.object(consumer_module.aio_pika, "connect_robust", AsyncMock(side_effect=connect_side_effect)):
            try:
                await coro_factory()
            except asyncio.CancelledError:
                pass

    asyncio.run(scenario())


@given("a fake broker with one good message and one poison message")
def step_broker_messages(context):
    context.handler = Mock()
    context.handler.handle = AsyncMock()

    channel = Mock()
    channel.set_qos = AsyncMock()
    channel.declare_exchange = AsyncMock(return_value=Mock())
    good = _FakeMessage(_good_body())
    poison = _FakeMessage(b"not-json-at-all")
    queue = _FakeQueue([good, poison])
    channel.declare_queue = AsyncMock(return_value=queue)

    context.connection = _FakeConnection(channel)
    context.good_message = good
    context.poison_message = poison


@given("a fake broker that fails to connect once")
def step_broker_fails(context):
    context.handler = Mock()
    context.handler.handle = AsyncMock()


@when("the evolution consumer runs one connection cycle")
def step_run(context):
    if hasattr(context, "connection"):
        _run_one_cycle(
            lambda: consumer_module.consume("amqp://fake", "evolution", context.handler),
            [context.connection, asyncio.CancelledError],
        )
    else:
        with patch.object(consumer_module.asyncio, "sleep", AsyncMock()) as fake_sleep:
            _run_one_cycle(
                lambda: consumer_module.consume("amqp://fake", "evolution", context.handler),
                [RuntimeError("connection refused"), asyncio.CancelledError],
            )
            context.fake_sleep = fake_sleep


@then("the good message was handled and acked")
def step_assert_handled(context):
    context.handler.handle.assert_awaited_once()
    context.good_message.ack.assert_awaited_once()


@then("the poison message was discarded without being handled")
def step_assert_discarded(context):
    # Unparseable JSON hits `continue` inside `message.process()`, which exits
    # the context manager normally — i.e. acked (discarded), never nacked —
    # same "give up on poison messages" behavior as worker/whatsapp/worker.py.
    context.poison_message.ack.assert_awaited_once()
    context.poison_message.nack.assert_not_awaited()
    context.handler.handle.assert_awaited_once()


@then("the connection was retried after the reconnect delay")
def step_assert_retried(context):
    context.fake_sleep.assert_awaited_with(consumer_module.RECONNECT_DELAY)
