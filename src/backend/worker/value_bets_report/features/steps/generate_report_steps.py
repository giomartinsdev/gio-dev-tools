from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock

from behave import given, then, use_step_matcher, when

from src.application.generate_report import ReportGenerator
from src.domain.report import REPORT_TIMEZONE
from src.infrastructure.recipients_repository import Recipient

use_step_matcher("re")

_REFERENCE_DAY_OFFSET = 1


def _value_bet_for_offset(days: int) -> dict:
    kickoff = datetime.now(REPORT_TIMEZONE) + timedelta(days=days)
    kickoff = kickoff.replace(hour=15, minute=0, second=0, microsecond=0)
    return {
        "match_id": "m1",
        "market": "1x2",
        "outcome": "HOME",
        "model_probability": "0.5",
        "bookmaker": "pinnacle",
        "best_odds": "2.5",
        "implied_probability": "0.4",
        "edge": "0.1",
        "detected_at": kickoff.isoformat(),
        "kickoff_at": kickoff.isoformat(),
        "status": "SCHEDULED",
        "home_team_name": "Team A",
        "away_team_name": "Team B",
    }


def _setup(context):
    context.config_repo = Mock()
    context.config_repo.get.return_value = Mock(reference_day_offset=_REFERENCE_DAY_OFFSET)
    context.value_bets_client = Mock()
    context.recipients_repo = Mock()
    context.whatsapp_publisher = Mock()
    context.whatsapp_publisher.publish = AsyncMock()
    context.generator = ReportGenerator(
        value_bets_client=context.value_bets_client,
        config_repo=context.config_repo,
        recipients_repo=context.recipients_repo,
        whatsapp_publisher=context.whatsapp_publisher,
    )


@given('the value bets client returns 1 bet for tomorrow')
def step_value_bets_tomorrow(context):
    _setup(context)
    context.value_bets_client.fetch = AsyncMock(return_value=[_value_bet_for_offset(_REFERENCE_DAY_OFFSET)])


@given('the value bets client returns 1 bet for the day after tomorrow')
def step_value_bets_day_after(context):
    _setup(context)
    context.value_bets_client.fetch = AsyncMock(return_value=[_value_bet_for_offset(_REFERENCE_DAY_OFFSET + 1)])


@given(r'(\d+) active recipients? and (\d+) inactive recipients?')
def step_mixed_recipients(context, active_count, inactive_count):
    active = [
        Recipient(id=i, phone_number=f"55119999999{i:02d}", name=None, active=True)
        for i in range(int(active_count))
    ]
    context.recipients_repo.list_active.return_value = active
    context.expected_numbers = {r.phone_number for r in active}


@given('no active recipients')
def step_no_active_recipients(context):
    context.recipients_repo.list_active.return_value = []
    context.expected_numbers = set()


@given(r'(\d+) active recipients?')
def step_active_recipients(context, count):
    active = [
        Recipient(id=i, phone_number=f"55119999999{i:02d}", name=None, active=True)
        for i in range(int(count))
    ]
    context.recipients_repo.list_active.return_value = active
    context.expected_numbers = {r.phone_number for r in active}


@when('the report generator runs')
def step_run_generator(context):
    asyncio.run(context.generator.run())


@then('a whatsapp message was published to each active recipient')
def step_assert_published_to_each(context):
    published_numbers = {call.args[0] for call in context.whatsapp_publisher.publish.await_args_list}
    assert published_numbers == context.expected_numbers, published_numbers


@then('no whatsapp message was published')
def step_assert_none_published(context):
    context.whatsapp_publisher.publish.assert_not_awaited()
