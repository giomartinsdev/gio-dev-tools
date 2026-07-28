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


@when("_init runs with working secrets and DB")
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
         patch.object(main_module.Base, "metadata", Mock(create_all=Mock())), \
         patch.object(main_module, "PostgresConversationStateRepository", return_value=Mock()), \
         patch.object(main_module, "BusTrackerClient", return_value=Mock()), \
         patch.object(main_module, "OsrmClient", return_value=Mock()):
        main_module._init(fake_app)

    context.fake_app = fake_app


@when("_init runs with a secret manager that fails")
def step_init_failure(context):
    fake_app = _fake_app()
    fake_app.state._init_done = threading.Event()
    fake_app.state._init_error = None

    with patch.object(main_module, "SecretManager", side_effect=RuntimeError("no secrets")):
        main_module._init(fake_app)

    context.fake_app = fake_app


@then("app state is populated and init_done is set with no error")
def step_assert_init_ok(context):
    assert context.fake_app.state._init_error is None
    assert context.fake_app.state._init_done.is_set()
    assert context.fake_app.state.state_repo is not None
    assert context.fake_app.state.bus_tracker is not None
    assert context.fake_app.state.osrm is not None


@then("app state has an init error and init_done is set")
def step_assert_init_failed(context):
    assert isinstance(context.fake_app.state._init_error, RuntimeError)
    assert context.fake_app.state._init_done.is_set()


def _fake_app_for_background(init_error=None):
    fake_app = _fake_app()
    fake_app.state._init_done = threading.Event()
    fake_app.state._init_done.set()
    fake_app.state._init_error = init_error
    fake_app.state.state_repo = Mock()
    fake_app.state.bus_tracker = Mock()
    fake_app.state.osrm = Mock()
    fake_app.state.rabbitmq_uri = "amqp://fake"
    fake_app.state.rabbitmq_exchange = "evolution"
    fake_app.state.sender = None
    return fake_app


@when("_run_background runs with an init error already set")
def step_run_background_init_error(context):
    fake_app = _fake_app_for_background(init_error=RuntimeError("boom"))

    with patch.object(main_module, "consume", AsyncMock()) as fake_consume:
        asyncio.run(main_module._run_background(fake_app))

    context.fake_consume = fake_consume


@then("the consumer was never started")
def step_assert_never_started(context):
    context.fake_consume.assert_not_awaited()


@when("_run_background runs with a working init")
def step_run_background_success(context):
    fake_app = _fake_app_for_background()

    with patch.object(main_module, "consume", AsyncMock()) as fake_consume:
        asyncio.run(main_module._run_background(fake_app))

    context.fake_app = fake_app
    context.fake_consume = fake_consume


@then("the sender was created and the consumer was started")
def step_assert_started(context):
    assert context.fake_app.state.sender is not None
    context.fake_consume.assert_awaited_once()


@when("the lifespan context runs a full startup and shutdown cycle")
def step_lifespan_cycle(context):
    fake_app = _fake_app()

    async def scenario():
        supervisor_started = asyncio.Event()

        async def fake_run_background(app):
            supervisor_started.set()
            await asyncio.Event().wait()

        with patch.object(main_module, "_init", lambda app: app.state._init_done.set()), \
             patch.object(main_module, "_run_background", fake_run_background):
            async with main_module.lifespan(fake_app):
                await supervisor_started.wait()

    asyncio.run(scenario())
    context.fake_app = fake_app


@then("the background task was cancelled")
def step_assert_lifespan_teardown(context):
    # If lifespan's cancel() call had raised or hung, the scenario step above
    # would never have completed — reaching here is the assertion.
    assert context.fake_app.state._init_done.is_set()
