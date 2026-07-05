from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
from unittest.mock import Mock, patch

from behave import given, then, use_step_matcher, when

from src.infrastructure.event_store_repository import EventStoreRepository

use_step_matcher("re")


class _FakeTransactionManager:
    def __init__(self, session):
        self._session = session

    @contextmanager
    def session(self):
        yield self._session


@given('a fake transaction manager for the event store repository')
def step_fake_tm(context):
    context.session = Mock()
    context.repo = EventStoreRepository()
    context.result = None
    fake_tm = _FakeTransactionManager(context.session)
    tm_patch = patch(
        "src.infrastructure.event_store_repository.TransactionManager.get", return_value=fake_tm,
    )
    tm_patch.start()
    context.add_cleanup(tm_patch.stop)


@given(r'the session reports (\d+) rows? affected')
def step_session_rowcount(context, rowcount):
    context.session.execute.return_value = Mock(rowcount=int(rowcount))


@when('I append an event to the store')
def step_append(context):
    context.result = context.repo.append(
        event_id="11111111-1111-1111-1111-111111111111",
        event_type="raw.feed_received",
        occurred_at=datetime.now(timezone.utc),
        payload={"x": 1},
    )


@then('append reports True')
def step_true(context):
    assert context.result is True


@then('append reports False')
def step_false(context):
    assert context.result is False
