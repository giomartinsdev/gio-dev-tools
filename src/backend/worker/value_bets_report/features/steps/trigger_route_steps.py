from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, Mock

from behave import given, then, use_step_matcher, when

from app.router import trigger_now

use_step_matcher("re")


@given('a trigger publisher')
def step_publisher(context):
    context.publisher = Mock()
    context.publisher.publish = AsyncMock()


@when('I call the trigger_now endpoint')
def step_call_trigger(context):
    context.result = asyncio.run(trigger_now(publisher=context.publisher))


@then('the trigger publisher published with reason "([^"]+)"')
def step_assert_published(context, reason):
    context.publisher.publish.assert_awaited_once_with(reason=reason)
