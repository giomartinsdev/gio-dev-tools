from __future__ import annotations

import asyncio
import threading
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from behave import given, then, use_step_matcher, when
from fastapi import HTTPException

import app.main as main_module
from app.deps import _ready

use_step_matcher("re")


def _fake_app():
    return SimpleNamespace(state=SimpleNamespace())


@when('_init runs with working secrets and DB')
def step_init_success(context):
    fake_app = _fake_app()
    fake_app.state._init_done = threading.Event()
    fake_app.state._init_error = None

    fake_sm = Mock()
    fake_sm.get_secret.side_effect = lambda k: f"secret-{k}"
    fake_tm_instance = Mock(engine=Mock())

    with patch.object(main_module, "SecretManager", return_value=fake_sm), \
         patch.object(main_module.TransactionManager, "configure"), \
         patch.object(main_module.TransactionManager, "get", return_value=fake_tm_instance), \
         patch.object(main_module, "create_all"), \
         patch.object(main_module, "ConfigRepository", return_value=Mock()), \
         patch.object(main_module, "RecipientsRepository", return_value=Mock()), \
         patch.object(main_module, "TriggerPublisher", return_value=Mock()), \
         patch.object(main_module, "ReportGenerator", return_value=Mock()), \
         patch.object(main_module, "ValueBetsClient", return_value=Mock()), \
         patch.object(main_module, "WhatsAppPublisher", return_value=Mock()):
        main_module._init(fake_app)

    context.fake_app = fake_app


@when('_init runs with a secret manager that fails')
def step_init_failure(context):
    fake_app = _fake_app()
    fake_app.state._init_done = threading.Event()
    fake_app.state._init_error = None

    with patch.object(main_module, "SecretManager", side_effect=RuntimeError("no secrets")):
        main_module._init(fake_app)

    context.fake_app = fake_app


@then('app state is populated and init_done is set with no error')
def step_assert_init_ok(context):
    assert context.fake_app.state._init_error is None
    assert context.fake_app.state._init_done.is_set()
    assert context.fake_app.state.config_repo is not None
    assert context.fake_app.state.recipients_repo is not None
    assert context.fake_app.state.trigger_publisher is not None
    assert context.fake_app.state.report_generator is not None


@then('app state has an init error and init_done is set')
def step_assert_init_failed(context):
    assert isinstance(context.fake_app.state._init_error, RuntimeError)
    assert context.fake_app.state._init_done.is_set()


def _fake_app_for_background(init_error=None):
    fake_app = _fake_app()
    fake_app.state._init_done = threading.Event()
    fake_app.state._init_done.set()
    fake_app.state._init_error = init_error
    fake_app.state.config_repo = Mock()
    fake_app.state.recipients_repo = Mock()
    fake_app.state.trigger_publisher = Mock()
    fake_app.state.report_generator = Mock()
    fake_app.state.rabbitmq_uri = "amqp://fake"
    return fake_app


@when('_run_background runs with an init error already set')
def step_run_background_init_error(context):
    fake_app = _fake_app_for_background(init_error=RuntimeError("boom"))
    with patch.object(main_module, "consume_triggers", AsyncMock()) as fake_consume, \
         patch.object(main_module, "DailyScheduler") as fake_scheduler_cls:
        fake_scheduler_cls.return_value.run = AsyncMock()
        asyncio.run(main_module._run_background(fake_app))
    context.fake_consume = fake_consume
    context.fake_scheduler_cls = fake_scheduler_cls


@then('neither the scheduler nor the trigger consumer were started')
def step_assert_neither_started(context):
    context.fake_consume.assert_not_awaited()
    context.fake_scheduler_cls.return_value.run.assert_not_awaited()


@when('_run_background runs with init already done successfully')
def step_run_background_success(context):
    fake_app = _fake_app_for_background()
    with patch.object(main_module, "consume_triggers", AsyncMock()) as fake_consume, \
         patch.object(main_module, "DailyScheduler") as fake_scheduler_cls:
        fake_scheduler_cls.return_value.run = AsyncMock()
        asyncio.run(main_module._run_background(fake_app))
    context.fake_consume = fake_consume
    context.fake_scheduler_cls = fake_scheduler_cls


@then('both the scheduler and the trigger consumer were started')
def step_assert_both_started(context):
    context.fake_consume.assert_awaited_once()
    context.fake_scheduler_cls.return_value.run.assert_awaited_once()


@when('the lifespan context runs a full startup and shutdown cycle')
def step_lifespan_cycle(context):
    fake_app = _fake_app()

    async def fake_run_background(app):
        await asyncio.Event().wait()

    async def scenario():
        with patch.object(main_module, "_init", lambda app: app.state._init_done.set()), \
             patch.object(main_module, "_run_background", fake_run_background):
            async with main_module.lifespan(fake_app):
                await asyncio.sleep(0)

    asyncio.run(scenario())
    context.fake_app = fake_app


@then('the background task was cancelled')
def step_assert_cancelled(context):
    assert context.fake_app.state._init_done.is_set()


def _fake_request(**state_kwargs):
    return SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(**state_kwargs)))


@given('app state with init done and no error')
def step_state_ok(context):
    init_done = threading.Event()
    init_done.set()
    context.request = _fake_request(_init_done=init_done, _init_error=None)
    context.error = None


@given('app state with init done and an init error')
def step_state_error(context):
    init_done = threading.Event()
    init_done.set()
    context.request = _fake_request(_init_done=init_done, _init_error=RuntimeError("boom"))
    context.error = None


@when('I call _ready')
def step_call_ready(context):
    _ready(context.request)


@when('I call _ready expecting an error')
def step_call_ready_error(context):
    try:
        _ready(context.request)
    except HTTPException as e:
        context.error = e


@then('no exception is raised')
def step_no_exception(context):
    assert context.error is None


@then('a 503 HTTPException is raised')
def step_503(context):
    assert isinstance(context.error, HTTPException)
    assert context.error.status_code == 503
