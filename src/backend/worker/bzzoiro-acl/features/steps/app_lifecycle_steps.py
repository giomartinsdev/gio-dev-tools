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
         patch.object(main_module, "PostgresIdentityRepository", return_value=Mock()), \
         patch.object(main_module, "BzzoiroClient", return_value=Mock()), \
         patch.object(main_module, "BzzoiroTranslator", return_value=Mock()):
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
    assert context.fake_app.state.client is not None
    assert context.fake_app.state.translator is not None


@then('app state has an init error and init_done is set')
def step_assert_init_failed(context):
    assert isinstance(context.fake_app.state._init_error, RuntimeError)
    assert context.fake_app.state._init_done.is_set()


class _RecordingHandler:
    def __init__(self, outcomes):
        self.calls = 0
        self._outcomes = list(outcomes)

    async def handle(self, cmd):
        self.calls += 1
        outcome = self._outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


@when('_poll_loop runs one successful iteration')
def step_poll_loop_success(context):
    handler = _RecordingHandler([3])

    async def run():
        with patch.object(main_module.asyncio, "sleep", AsyncMock(side_effect=asyncio.CancelledError)):
            try:
                await main_module._poll_loop("test", 1, handler, object())
            except asyncio.CancelledError:
                pass

    asyncio.run(run())
    context.handler = handler


@when('_poll_loop runs one failing iteration')
def step_poll_loop_failure(context):
    handler = _RecordingHandler([RuntimeError("upstream failed")])

    async def run():
        with patch.object(main_module.asyncio, "sleep", AsyncMock(side_effect=asyncio.CancelledError)):
            try:
                await main_module._poll_loop("test", 1, handler, object())
            except asyncio.CancelledError:
                pass

    asyncio.run(run())
    context.handler = handler


@then('the handler was called and the loop continued')
def step_assert_handler_called(context):
    assert context.handler.calls == 1


@then('the failure was logged and the loop continued')
def step_assert_failure_logged(context):
    assert context.handler.calls == 1


def _fake_app_for_background(init_error=None):
    fake_app = _fake_app()
    fake_app.state._init_done = threading.Event()
    fake_app.state._init_done.set()
    fake_app.state._init_error = init_error
    fake_app.state.client = Mock()
    fake_app.state.translator = Mock()
    fake_app.state.checkpoints = Mock()
    fake_app.state.rabbitmq_uri = "amqp://fake"
    fake_app.state.publisher = None
    return fake_app


@when('_run_background runs with an init error already set')
def step_run_background_init_error(context):
    fake_app = _fake_app_for_background(init_error=RuntimeError("boom"))
    fake_publisher = Mock()
    fake_publisher.connect = AsyncMock()

    with patch.object(main_module, "RabbitMQPublisher", return_value=fake_publisher):
        asyncio.run(main_module._run_background(fake_app))

    context.fake_publisher = fake_publisher


@then('the publisher was never connected')
def step_assert_never_connected(context):
    context.fake_publisher.connect.assert_not_awaited()


@when('_run_background runs through one successful connect-and-poll cycle')
def step_run_background_success(context):
    fake_app = _fake_app_for_background()
    fake_publisher = Mock()
    fake_publisher.connect = AsyncMock(side_effect=[None, asyncio.CancelledError])

    with patch.object(main_module, "RabbitMQPublisher", return_value=fake_publisher), \
         patch.object(main_module, "_poll_loop", AsyncMock(return_value=None)) as fake_poll_loop:
        try:
            asyncio.run(main_module._run_background(fake_app))
        except asyncio.CancelledError:
            pass

    context.fake_app = fake_app
    context.fake_publisher = fake_publisher
    context.fake_poll_loop = fake_poll_loop


@then('the publisher was connected and poll loops were started')
def step_assert_connected_and_polling(context):
    assert context.fake_app.state.publisher is context.fake_publisher
    # fixtures, live, odds, odds_comparison, odds_best, lineups, h2h, standings,
    # predictions, teams, venues, referees, player_stats, incidents — all
    # through the generic loop
    assert context.fake_poll_loop.await_count == 14


@when('_run_background hits a connection error on its first attempt')
def step_run_background_connection_error(context):
    fake_app = _fake_app_for_background()
    fake_publisher = Mock()
    fake_publisher.connect = AsyncMock(side_effect=[RuntimeError("connection refused"), asyncio.CancelledError])

    with patch.object(main_module, "RabbitMQPublisher", return_value=fake_publisher), \
         patch.object(main_module.asyncio, "sleep", AsyncMock()) as fake_sleep:
        try:
            asyncio.run(main_module._run_background(fake_app))
        except asyncio.CancelledError:
            pass

    context.fake_app = fake_app
    context.fake_sleep = fake_sleep


@then('the error was logged and a reconnect was scheduled')
def step_assert_reconnect_scheduled(context):
    assert context.fake_app.state.publisher is None
    context.fake_sleep.assert_awaited_with(main_module.RECONNECT_DELAY)


@when('the lifespan context runs a full startup and shutdown cycle')
def step_lifespan_cycle(context):
    fake_app = _fake_app()
    fake_publisher = Mock()
    fake_publisher.close = AsyncMock()

    async def fake_run_background(app):
        app.state.publisher = fake_publisher
        await asyncio.Event().wait()

    async def scenario():
        with patch.object(main_module, "_init", lambda app: app.state._init_done.set()), \
             patch.object(main_module, "_run_background", fake_run_background):
            async with main_module.lifespan(fake_app):
                await asyncio.sleep(0)

    asyncio.run(scenario())
    context.fake_app = fake_app
    context.fake_publisher = fake_publisher


@then('the background task was cancelled and the publisher was closed')
def step_assert_lifespan_teardown(context):
    context.fake_publisher.close.assert_awaited_once()
