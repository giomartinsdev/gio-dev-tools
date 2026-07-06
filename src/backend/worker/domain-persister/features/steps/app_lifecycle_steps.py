from __future__ import annotations

import asyncio
import threading
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from behave import then, use_step_matcher, when

import app.main as main_module

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
         patch.object(main_module, "ReadModelRepository", return_value=Mock()), \
         patch.object(main_module, "EventStoreRepository", return_value=Mock()):
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
    assert context.fake_app.state.read_models is not None
    assert context.fake_app.state.event_store is not None


@then('app state has an init error and init_done is set')
def step_assert_init_failed(context):
    assert isinstance(context.fake_app.state._init_error, RuntimeError)
    assert context.fake_app.state._init_done.is_set()


def _fake_app_for_background(init_error=None):
    fake_app = _fake_app()
    fake_app.state._init_done = threading.Event()
    fake_app.state._init_done.set()
    fake_app.state._init_error = init_error
    fake_app.state.read_models = Mock()
    fake_app.state.event_store = Mock()
    fake_app.state.rabbitmq_uri = "amqp://fake"
    return fake_app


@when('_run_background runs with an init error already set')
def step_run_background_init_error(context):
    fake_app = _fake_app_for_background(init_error=RuntimeError("boom"))
    with patch.object(main_module, "run_consumers", AsyncMock()) as fake_run_consumers:
        asyncio.run(main_module._run_background(fake_app))
    context.fake_run_consumers = fake_run_consumers


@then('run_consumers was never called')
def step_assert_never_called(context):
    context.fake_run_consumers.assert_not_awaited()


@when('_run_background runs with init already done successfully')
def step_run_background_success(context):
    fake_app = _fake_app_for_background()
    with patch.object(main_module, "run_consumers", AsyncMock()) as fake_run_consumers:
        asyncio.run(main_module._run_background(fake_app))
    context.fake_app = fake_app
    context.fake_run_consumers = fake_run_consumers


@then('run_consumers was called with the read models and event store')
def step_assert_called(context):
    context.fake_run_consumers.assert_awaited_once()
    args, _ = context.fake_run_consumers.await_args
    assert args[0] == "amqp://fake"
    assert args[1] is context.fake_app.state.event_store


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
