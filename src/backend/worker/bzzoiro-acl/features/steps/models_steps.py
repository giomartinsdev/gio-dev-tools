from __future__ import annotations

from unittest.mock import MagicMock, patch

from behave import given, then, use_step_matcher, when

import src.infrastructure.models as models_module

use_step_matcher("re")


@given('a mocked engine')
def step_mocked_engine(context):
    context.calls = []
    conn = MagicMock()
    conn.execute.side_effect = lambda stmt: context.calls.append(("execute", str(stmt)))
    engine = MagicMock()
    engine.begin.return_value.__enter__.return_value = conn
    context.engine = engine


@when('create_all runs against it')
def step_run_create_all(context):
    with patch.object(
        models_module.Base.metadata, "create_all",
        side_effect=lambda engine: context.calls.append(("create_all", engine)),
    ):
        models_module.create_all(context.engine)


@then('the schema was created before the tables')
def step_assert_order(context):
    assert context.calls[0][0] == "execute", context.calls
    assert "CREATE SCHEMA IF NOT EXISTS bzzoiro_data" in context.calls[0][1], context.calls
    assert context.calls[1] == ("create_all", context.engine), context.calls
