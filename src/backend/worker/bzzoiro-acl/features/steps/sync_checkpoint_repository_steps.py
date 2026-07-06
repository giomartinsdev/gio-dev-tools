from __future__ import annotations

from behave import given, then, use_step_matcher, when

from shared.transaction_manager import TransactionConfig, TransactionManager
from src.infrastructure.models import Base
from src.infrastructure.sync_checkpoint_repository import SyncCheckpointRepository

use_step_matcher("re")


@given('a fresh sync checkpoint table')
def step_fresh_table(context):
    TransactionManager.reset()
    TransactionManager.configure(TransactionConfig(url="sqlite:///:memory:"))
    engine = TransactionManager.get().engine
    # SQLite has no CREATE SCHEMA; ATTACH a second in-memory DB under the
    # "bzzoiro_data" alias so the schema-qualified table name resolves.
    with engine.begin() as conn:
        conn.exec_driver_sql("ATTACH DATABASE ':memory:' AS bzzoiro_data")
    Base.metadata.create_all(engine)
    context.repo = SyncCheckpointRepository()
    context.cursor = "unset"


@given(r'the cursor for "([^"]+)" is "([^"]+)"')
def step_given_cursor(context, feed_type, cursor):
    context.repo.set_cursor(feed_type, cursor)


@when(r'I set the cursor for "([^"]+)" to "([^"]+)"')
def step_set_cursor(context, feed_type, cursor):
    context.repo.set_cursor(feed_type, cursor)


@when(r'I get the cursor for "([^"]+)"')
def step_get_cursor(context, feed_type):
    context.cursor = context.repo.get_cursor(feed_type)


@when(r'I clear the checkpoint for "([^"]+)"')
def step_clear(context, feed_type):
    context.repo.clear(feed_type)


@when('I clear all checkpoints')
def step_clear_all(context):
    context.repo.clear_all()


@then(r'the cursor is "([^"]+)"')
def step_assert_cursor(context, expected):
    assert context.cursor == expected, f"expected {expected!r}, got {context.cursor!r}"


@then('the cursor is None')
def step_assert_cursor_none(context):
    assert context.cursor is None, f"expected None, got {context.cursor!r}"
