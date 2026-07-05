from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock, patch
from uuid import uuid4

from behave import given, then, use_step_matcher, when

from src.infrastructure.read_model_repository import ReadModelRepository

use_step_matcher("re")


class _FakeTransactionManager:
    def __init__(self, session):
        self._session = session

    @contextmanager
    def session(self):
        yield self._session

    @contextmanager
    def read_only(self):
        yield self._session


@given('a fake transaction manager for the read model repository')
def step_fake_tm(context):
    context.session = Mock()
    context.repo = ReadModelRepository()
    context.result = None
    fake_tm = _FakeTransactionManager(context.session)
    tm_patch = patch(
        "src.infrastructure.read_model_repository.TransactionManager.get", return_value=fake_tm,
    )
    tm_patch.start()
    context.add_cleanup(tm_patch.stop)


@when('I upsert a scheduled match')
def step_upsert_scheduled(context):
    context.repo.upsert_match_scheduled(
        match_id=uuid4(), competition_id=uuid4(), home_team_id=uuid4(), away_team_id=uuid4(),
        kickoff_at=datetime.now(timezone.utc), venue="Emirates",
    )


@when('I upsert a match status')
def step_upsert_status(context):
    context.repo.upsert_match_status(match_id=uuid4(), status="LIVE", minute=12)


@when('I upsert a match score')
def step_upsert_score(context):
    context.repo.upsert_match_score(match_id=uuid4(), home_score=1, away_score=0, minute=30)


@when('I upsert a finished match')
def step_upsert_finished(context):
    context.repo.upsert_match_finished(match_id=uuid4(), home_score=2, away_score=1, statistics={"shots": 10})


@when('I insert an odds snapshot')
def step_insert_odds(context):
    context.repo.insert_odds_snapshot(
        event_id=uuid4(), match_id=uuid4(), bookmaker="aggregate", market="1x2",
        selections=[{"name": "home", "price": "2.10"}], captured_at=datetime.now(timezone.utc),
    )


@then(r'the session executed a statement against "([^"]+)"')
def step_assert_table(context, table_name):
    context.session.execute.assert_called_once()
    stmt = context.session.execute.call_args[0][0]
    assert stmt.table.name == table_name, f"expected {table_name}, got {stmt.table.name}"


def _fake_match_row():
    return SimpleNamespace(
        match_id=str(uuid4()), competition_id=str(uuid4()), home_team_id=str(uuid4()),
        away_team_id=str(uuid4()), status="LIVE", home_score=1, away_score=0, minute=10,
        kickoff_at=datetime.now(timezone.utc), venue="Emirates", statistics=None,
    )


@given('the session query returns 1 match row')
def step_query_returns_row(context):
    row = _fake_match_row()
    context.session.query.return_value.order_by.return_value.limit.return_value.offset.return_value.all.return_value = [row]


@given('the session get returns a match row')
def step_get_returns_row(context):
    context.session.get.return_value = _fake_match_row()


@given('the session get returns no row')
def step_get_returns_none(context):
    context.session.get.return_value = None


@when('I list all matches')
def step_list_matches(context):
    context.result = context.repo.find_all_matches()


@when('I get that match')
def step_get_match(context):
    context.result = context.repo.find_match("some-id")


@then(r'(\d+) match dicts? (?:is|are) returned')
def step_assert_n_matches(context, count):
    assert len(context.result) == int(count)


@then('a match dict is returned')
def step_assert_match_dict(context):
    assert context.result is not None
    assert "match_id" in context.result


@then('None is returned')
def step_assert_none(context):
    assert context.result is None
