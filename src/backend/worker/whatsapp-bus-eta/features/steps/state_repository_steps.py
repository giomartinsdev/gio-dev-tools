from __future__ import annotations

from unittest.mock import MagicMock, patch

from behave import given, then, use_step_matcher, when

from src.infrastructure.state_repository import ConversationStateModel, PostgresConversationStateRepository

use_step_matcher("re")


def _make_session_cm(session):
    cm = MagicMock()
    cm.__enter__ = MagicMock(return_value=session)
    cm.__exit__ = MagicMock(return_value=False)
    return cm


def _fake_tm(session):
    tm = MagicMock()
    tm.session.return_value = _make_session_cm(session)
    tm.read_only.return_value = _make_session_cm(session)
    return tm


@given(r'no row exists for jid "([^"]+)"')
def step_no_row(context, jid):
    session = MagicMock()
    session.get = MagicMock(return_value=None)
    context.session = session
    context.tm = _fake_tm(session)
    context.repo = PostgresConversationStateRepository()


@given(r'a row exists for jid "([^"]+)" with lat (-?[\d.]+) lon (-?[\d.]+) mode "([^"]+)" line "([^"]+)"')
def step_row_exists(context, jid, lat, lon, mode, line_code):
    row = ConversationStateModel(remote_jid=jid, lat=float(lat), lon=float(lon), mode=mode, line_code=line_code)
    session = MagicMock()
    session.get = MagicMock(return_value=row)
    context.session = session
    context.tm = _fake_tm(session)
    context.repo = PostgresConversationStateRepository()


@when(r'I get the state for jid "([^"]+)"')
def step_get_state(context, jid):
    with patch("src.infrastructure.state_repository.TransactionManager.get", return_value=context.tm):
        context.state = context.repo.get(jid)


@then("the state has no location and no line")
def step_assert_empty(context):
    assert not context.state.has_location
    assert not context.state.has_line


@then(r'the state has location (-?[\d.]+) (-?[\d.]+) and line "([^"]+)" "([^"]+)"')
def step_assert_state(context, lat, lon, mode, line_code):
    assert context.state.lat == float(lat)
    assert context.state.lon == float(lon)
    assert context.state.mode == mode
    assert context.state.line_code == line_code


@when(r'I set the location for jid "([^"]+)" to (-?[\d.]+) (-?[\d.]+)')
def step_set_location(context, jid, lat, lon):
    session = MagicMock()
    context.session = session
    context.tm = _fake_tm(session)
    context.repo = PostgresConversationStateRepository()
    with patch("src.infrastructure.state_repository.TransactionManager.get", return_value=context.tm):
        context.repo.set_location(jid, float(lat), float(lon))


@when(r'I set the line for jid "([^"]+)" to mode "([^"]+)" line "([^"]+)"')
def step_set_line(context, jid, mode, line_code):
    session = MagicMock()
    context.session = session
    context.tm = _fake_tm(session)
    context.repo = PostgresConversationStateRepository()
    with patch("src.infrastructure.state_repository.TransactionManager.get", return_value=context.tm):
        context.repo.set_line(jid, mode, line_code)


@then("an upsert was executed")
def step_assert_upsert(context):
    context.session.execute.assert_called_once()
