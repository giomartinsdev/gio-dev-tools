from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, Mock, patch

from behave import given, then, use_step_matcher, when

import src.infrastructure.whatsapp_notifier as notifier_module
from src.infrastructure.whatsapp_notifier import WhatsAppNotifier

use_step_matcher("re")


@given('a fresh whatsapp notifier')
def step_fresh_notifier(context):
    context.published = []

    channel = Mock()
    channel.declare_queue = AsyncMock()

    async def _publish(message, routing_key):
        context.published.append((routing_key, json.loads(message.body.decode())))

    channel.default_exchange = Mock()
    channel.default_exchange.publish = AsyncMock(side_effect=_publish)

    connection = Mock()
    connection.channel = AsyncMock(return_value=channel)
    connection.close = AsyncMock()

    context.connect_patch = patch.object(
        notifier_module.aio_pika, "connect_robust", AsyncMock(return_value=connection),
    )
    context.notifier = WhatsAppNotifier("amqp://fake", "5511999999999")


@given('the notifier has an instance configured')
def step_notifier_with_instance(context):
    context.notifier = WhatsAppNotifier("amqp://fake", "5511999999999", "admin")


@when(r'I send a notification with text "([^"]+)"')
def step_send_notification(context, text):
    with context.connect_patch:
        asyncio.run(context.notifier.notify(text))


@then(r'a message was published to the whatsapp-send queue with number and text "([^"]+)"')
def step_assert_published(context, text):
    assert context.published, "no message was published"
    routing_key, payload = context.published[0]
    assert routing_key == "whatsapp-send", routing_key
    assert payload["number"] == "5511999999999", payload
    assert payload["text"] == text, payload


@then('the published message includes the configured instance')
def step_assert_instance(context):
    _, payload = context.published[0]
    assert payload.get("instance") == "admin", payload
