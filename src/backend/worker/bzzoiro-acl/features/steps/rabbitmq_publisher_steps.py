from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from behave import given, then, use_step_matcher, when

from shared.events import EventMeta, MatchStatusChanged, MatchStatus
from src.infrastructure.rabbitmq_publisher import RabbitMQPublisher

use_step_matcher("re")


def _make_fake_channel():
    exchanges = {}

    async def _declare_exchange(name, *_args, **_kwargs):
        exchange = AsyncMock(name=f"exchange-{name}")
        exchanges[name] = exchange
        return exchange

    async def _get_exchange(name):
        return exchanges[name]

    fake_queue = AsyncMock()
    fake_queue.bind = AsyncMock()

    channel = AsyncMock()
    channel.declare_exchange = AsyncMock(side_effect=_declare_exchange)
    channel.declare_queue = AsyncMock(return_value=fake_queue)
    channel.get_exchange = AsyncMock(side_effect=_get_exchange)
    return channel, exchanges


@given('a connected fake RabbitMQ publisher')
def step_connected_publisher(context):
    channel, exchanges = _make_fake_channel()
    connection = AsyncMock()
    connection.channel = AsyncMock(return_value=channel)
    connection.close = AsyncMock()

    context.fake_connection = connection
    context.fake_exchanges = exchanges
    context.publisher = RabbitMQPublisher(uri="amqp://fake")

    async def _connect():
        with patch("aio_pika.connect_robust", AsyncMock(return_value=connection)):
            await context.publisher.connect()

    asyncio.run(_connect())


@when('I publish a raw "fixtures" feed')
def step_publish_raw(context):
    asyncio.run(context.publisher.publish_raw("fixtures", "provider-123", {"a": 1}))


@when('I publish a MatchStatusChanged domain event')
def step_publish_domain_event(context):
    event = MatchStatusChanged(
        meta=EventMeta(occurred_at=datetime.now(timezone.utc), producer="acl.bzzoiro", correlation_id=uuid4()),
        match_id=uuid4(),
        status=MatchStatus.LIVE,
        minute=10,
    )
    asyncio.run(context.publisher.publish_domain_event(event))


@when('I close the publisher')
def step_close_publisher(context):
    asyncio.run(context.publisher.close())


@then(r'the ingestion exchange received a message with routing key "([^"]+)"')
def step_assert_ingestion_routing_key(context, routing_key):
    exchange = context.fake_exchanges["ingestion.events"]
    exchange.publish.assert_awaited_once()
    _, kwargs = exchange.publish.await_args
    assert kwargs["routing_key"] == routing_key, f"expected {routing_key}, got {kwargs['routing_key']}"


@then(r'the domain exchange received a message with routing key "([^"]+)"')
def step_assert_domain_routing_key(context, routing_key):
    exchange = context.fake_exchanges["domain.events"]
    exchange.publish.assert_awaited_once()
    _, kwargs = exchange.publish.await_args
    assert kwargs["routing_key"] == routing_key, f"expected {routing_key}, got {kwargs['routing_key']}"


@then('the underlying connection was closed')
def step_assert_connection_closed(context):
    context.fake_connection.close.assert_awaited_once()
