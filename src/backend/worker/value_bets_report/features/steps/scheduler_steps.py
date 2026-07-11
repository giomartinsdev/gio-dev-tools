from __future__ import annotations

import asyncio
from contextlib import nullcontext
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

from behave import given, then, use_step_matcher, when

import src.application.scheduler as scheduler_module
from src.application.scheduler import DailyScheduler, compute_next_fire
from src.domain.report import REPORT_TIMEZONE

use_step_matcher("re")


@given('the current time is "([^"]+)" in the report timezone')
def step_current_time(context, iso_time):
    context.now = datetime.fromisoformat(iso_time).replace(tzinfo=REPORT_TIMEZONE)


@when('I compute the next fire time for send_time "([^"]+)"')
def step_compute_next_fire(context, send_time):
    context.result = compute_next_fire(context.now, send_time)


@then('the next fire time is "([^"]+)" in the report timezone')
def step_assert_next_fire(context, iso_time):
    expected = datetime.fromisoformat(iso_time).replace(tzinfo=REPORT_TIMEZONE)
    assert context.result == expected, context.result


class _StopLoop(Exception):
    pass


@given('a scheduler with enabled config and send_time "([^"]+)"')
def step_scheduler_enabled(context, send_time):
    config = Mock(enabled=True, send_time=send_time)
    context.config_repo = Mock()
    context.config_repo.get.return_value = config
    context.trigger_publisher = Mock()
    context.trigger_publisher.publish = AsyncMock()
    context.scheduler = DailyScheduler(context.config_repo, context.trigger_publisher)

    # First sleep (the wait until fire time) is a no-op; second sleep (start
    # of the next loop iteration) raises to stop the otherwise-infinite loop
    # once we've observed one publish.
    context.sleep_patch = patch.object(
        scheduler_module.asyncio, "sleep", AsyncMock(side_effect=[None, _StopLoop()]),
    )

    # Controls "now" across the run: just before midnight (so next_fire is
    # tomorrow at send_time "00:00"), then just after — three calls happen
    # before the loop's second sleep raises to stop it.
    just_before = datetime(2026, 7, 11, 23, 59, tzinfo=REPORT_TIMEZONE)
    just_after = datetime(2026, 7, 12, 0, 0, 1, tzinfo=REPORT_TIMEZONE)
    fake_datetime = Mock()
    fake_datetime.now = Mock(side_effect=[just_before, just_after, just_after])
    context.datetime_patch = patch.object(scheduler_module, "datetime", fake_datetime)


@given('a scheduler with disabled config')
def step_scheduler_disabled(context):
    config = Mock(enabled=False, send_time="00:00")
    context.config_repo = Mock()
    context.config_repo.get.return_value = config
    context.trigger_publisher = Mock()
    context.trigger_publisher.publish = AsyncMock()
    context.scheduler = DailyScheduler(context.config_repo, context.trigger_publisher)

    context.sleep_patch = patch.object(
        scheduler_module.asyncio, "sleep", AsyncMock(side_effect=[None, _StopLoop()]),
    )
    context.datetime_patch = nullcontext()


@when('the scheduler runs one cycle')
def step_run_scheduler(context):
    async def _run():
        try:
            await context.scheduler.run()
        except _StopLoop:
            pass

    with context.sleep_patch, context.datetime_patch:
        asyncio.run(_run())


@then('a trigger was published with reason "([^"]+)"')
def step_assert_published(context, reason):
    context.trigger_publisher.publish.assert_awaited_once_with(reason=reason)


@then('no trigger was published')
def step_assert_not_published(context):
    context.trigger_publisher.publish.assert_not_awaited()
