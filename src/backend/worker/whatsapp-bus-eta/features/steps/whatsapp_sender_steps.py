from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, patch

from behave import given, then, use_step_matcher, when

from src.infrastructure.whatsapp_sender import WhatsAppSender

use_step_matcher("re")


@given("a fake RabbitMQ connection")
def step_fake_connection(context):
    channel = AsyncMock()
    channel.declare_queue = AsyncMock()
    channel.default_exchange = AsyncMock()
    channel.default_exchange.publish = AsyncMock()

    connection = AsyncMock()
    connection.channel = AsyncMock(return_value=channel)

    context.fake_channel = channel
    context.fake_connection = connection
    context.sender = WhatsAppSender(rabbitmq_uri="amqp://fake")


@when(r'I send a WhatsApp reply to "([^"]+)" with text "([^"]+)"')
def step_send(context, number, text):
    async def run():
        with patch("aio_pika.connect_robust", AsyncMock(return_value=context.fake_connection)):
            await context.sender.send(number, text)

    asyncio.run(run())


@then(r'a message was published to queue "([^"]+)" with number "([^"]+)" and text "([^"]+)"')
def step_assert_published(context, queue, number, text):
    context.fake_channel.declare_queue.assert_awaited_once_with(queue, durable=True)
    context.fake_channel.default_exchange.publish.assert_awaited_once()
    args, kwargs = context.fake_channel.default_exchange.publish.await_args
    message = args[0]
    body = json.loads(message.body)
    assert body == {"number": number, "text": text}
    assert kwargs["routing_key"] == queue
