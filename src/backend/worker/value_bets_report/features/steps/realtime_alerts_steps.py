from __future__ import annotations

import asyncio
from decimal import Decimal
from unittest.mock import AsyncMock, Mock

from behave import given, then, use_step_matcher, when

from src.application.realtime_alerts import RealtimeAlertChecker
from src.infrastructure.recipients_repository import Recipient

use_step_matcher("re")


def _setup(context):
    context.config_repo = Mock()
    context.recipients_repo = Mock()
    context.recipients_repo.list_realtime_subscribers.return_value = []
    context.alert_log_repo = Mock()
    context.alert_log_repo.is_alerted.return_value = False
    context.value_bets_client = Mock()
    context.value_bets_client.fetch = AsyncMock(return_value=[])
    context.whatsapp_publisher = Mock()
    context.whatsapp_publisher.publish = AsyncMock()
    context.checker = RealtimeAlertChecker(
        value_bets_client=context.value_bets_client,
        config_repo=context.config_repo,
        recipients_repo=context.recipients_repo,
        alert_log_repo=context.alert_log_repo,
        whatsapp_publisher=context.whatsapp_publisher,
    )


@given('realtime alerts enabled with threshold "([^"]+)"')
def step_enabled(context, threshold):
    _setup(context)
    context.config_repo.get.return_value = Mock(
        realtime_alerts_enabled=True, realtime_edge_threshold=Decimal(threshold),
    )


@given('realtime alerts disabled')
def step_disabled(context):
    _setup(context)
    context.config_repo.get.return_value = Mock(realtime_alerts_enabled=False, realtime_edge_threshold=Decimal("0.2"))


@given(r'(\d+) realtime subscribers?')
def step_subscribers(context, count):
    subs = [
        Recipient(id=i, phone_number=f"55119999999{i:02d}", name=None, active=True, realtime_alerts=True)
        for i in range(int(count))
    ]
    context.recipients_repo.list_realtime_subscribers.return_value = subs
    context.expected_numbers = {r.phone_number for r in subs}


@given('no realtime subscribers')
def step_no_subscribers(context):
    context.recipients_repo.list_realtime_subscribers.return_value = []
    context.expected_numbers = set()


@given(r'the value bets client returns 1 value bet with edge "([^"]+)" not yet alerted')
def step_value_bet_not_alerted(context, edge):
    context.value_bets_client.fetch = AsyncMock(return_value=[_value_bet(edge)])
    context.alert_log_repo.is_alerted.return_value = False


@given(r'the value bets client returns 1 value bet with edge "([^"]+)" already alerted')
def step_value_bet_already_alerted(context, edge):
    context.value_bets_client.fetch = AsyncMock(return_value=[_value_bet(edge)])
    context.alert_log_repo.is_alerted.return_value = True


def _value_bet(edge: str) -> dict:
    return {
        "match_id": "m1", "market": "1x2", "outcome": "HOME", "edge": edge,
        "bookmaker": "pinnacle", "best_odds": "2.5", "kickoff_at": None,
        "home_team_name": "Team A", "away_team_name": "Team B",
    }


@when('the realtime alert checker runs one check')
def step_run_checker(context):
    asyncio.run(context.checker.check_once())


@then('a realtime alert was published to the subscriber')
def step_assert_published(context):
    published_numbers = {call.args[0] for call in context.whatsapp_publisher.publish.await_args_list}
    assert published_numbers == context.expected_numbers, published_numbers


@then('no realtime alert was published')
def step_assert_none_published(context):
    context.whatsapp_publisher.publish.assert_not_awaited()


@then('the value bet was marked as alerted')
def step_assert_marked(context):
    context.alert_log_repo.mark_alerted.assert_called_once_with("m1", "1x2", "HOME")
