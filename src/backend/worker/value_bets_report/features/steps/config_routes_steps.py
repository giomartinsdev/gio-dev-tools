from __future__ import annotations

from unittest.mock import Mock

from behave import given, then, use_step_matcher, when

from app.router import ConfigUpdate, get_config, put_config
from src.infrastructure.config_repository import ReportConfig

use_step_matcher("re")


@given(r'a config repository returning send_time "([^"]+)", offset (\d+), enabled')
def step_repo_returning(context, send_time, offset):
    context.repo = Mock()
    context.repo.get.return_value = ReportConfig(send_time=send_time, reference_day_offset=int(offset), enabled=True)


@given('a config repository')
def step_repo(context):
    context.repo = Mock()
    context.repo.update.return_value = ReportConfig(send_time="08:30", reference_day_offset=0, enabled=False)


@when('I call the get_config endpoint')
def step_call_get(context):
    context.result = get_config(repo=context.repo)


@when(r'I call the put_config endpoint with send_time "([^"]+)", offset (\d+), enabled (true|false)')
def step_call_put(context, send_time, offset, enabled):
    body = ConfigUpdate(send_time=send_time, reference_day_offset=int(offset), enabled=(enabled == "true"))
    context.result = put_config(body, repo=context.repo)


@then('the returned config has send_time "([^"]+)"')
def step_assert_send_time(context, send_time):
    assert context.result.send_time == send_time, context.result


@then(r'the config repository was updated with send_time "([^"]+)", offset (\d+), enabled (true|false)')
def step_assert_updated(context, send_time, offset, enabled):
    context.repo.update.assert_called_once_with(
        send_time=send_time, reference_day_offset=int(offset), enabled=(enabled == "true"),
    )
