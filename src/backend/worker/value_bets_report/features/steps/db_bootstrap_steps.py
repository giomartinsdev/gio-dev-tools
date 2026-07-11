from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

from behave import given, then, use_step_matcher, when

import src.infrastructure.db_bootstrap as db_bootstrap_module
from src.infrastructure.db_bootstrap import ensure_db

use_step_matcher("re")


def _fake_admin_conn(exists: bool):
    conn = AsyncMock()
    conn.fetchval = AsyncMock(return_value=1 if exists else None)
    conn.execute = AsyncMock()
    conn.close = AsyncMock()
    return conn


@given('an admin connection reporting the database is missing')
def step_admin_missing(context):
    context.conn = _fake_admin_conn(exists=False)
    context.connect_patch = patch.object(
        db_bootstrap_module.asyncpg, "connect", AsyncMock(return_value=context.conn),
    )


@given('an admin connection reporting the database already exists')
def step_admin_exists(context):
    context.conn = _fake_admin_conn(exists=True)
    context.connect_patch = patch.object(
        db_bootstrap_module.asyncpg, "connect", AsyncMock(return_value=context.conn),
    )


@when('I ensure the database exists')
def step_ensure_db(context):
    with context.connect_patch:
        asyncio.run(ensure_db("postgresql://user:pass@host:5432/value_bets_report"))


@then('a CREATE DATABASE statement was executed')
def step_assert_created(context):
    context.conn.execute.assert_called_once()
    assert "CREATE DATABASE" in context.conn.execute.call_args[0][0]


@then('no CREATE DATABASE statement was executed')
def step_assert_not_created(context):
    context.conn.execute.assert_not_called()
