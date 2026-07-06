from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from behave import given, then, use_step_matcher, when

from src.infrastructure.read_only_repository import _OVERVIEW_TABLES, ReadOnlyRepository

use_step_matcher("re")


class _FakeSession:
    def __init__(self, execute_results):
        self._results = list(execute_results)
        self._calls = 0

    def execute(self, stmt, params=None):
        result = self._results[self._calls]
        self._calls += 1
        return result


def _mock_result_for_one(**attrs):
    result = MagicMock()
    result.one.return_value = SimpleNamespace(**attrs)
    return result


def _mock_result_for_mappings(rows: list[dict]):
    result = MagicMock()
    result.mappings.return_value.all.return_value = rows
    return result


@contextmanager
def _fake_read_only(results):
    yield _FakeSession(results)


def _patch_transaction_manager(context, results):
    fake_tm = MagicMock()
    fake_tm.read_only.side_effect = lambda: _fake_read_only(results)
    context.tm_patch = patch(
        "src.infrastructure.read_only_repository.TransactionManager.get", return_value=fake_tm,
    )
    context.repo = ReadOnlyRepository()


@given('a fake transaction manager returning overview rows')
def step_overview_rows(context):
    now = datetime.now(timezone.utc)
    results = [
        _mock_result_for_one(rows=1, most_recent=now)
        for _ in _OVERVIEW_TABLES
    ]
    _patch_transaction_manager(context, results)


@given('a fake transaction manager returning 1 match row')
def step_one_match_row(context):
    row = {
        "match_id": "m1", "status": "LIVE", "home_score": 1, "away_score": 0, "minute": 60,
        "kickoff_at": datetime.now(timezone.utc), "venue": None,
        "home_team_name": "Team A", "away_team_name": "Team B",
    }
    results = [_mock_result_for_mappings([row])]
    _patch_transaction_manager(context, results)


@given('a fake transaction manager returning 1 value bet row')
def step_one_value_bet_row(context):
    row = {
        "match_id": "m1", "market": "1x2", "outcome": "HOME", "model_probability": "0.60",
        "bookmaker": "bet365", "best_odds": "2.20", "implied_probability": "0.4545",
        "edge": "0.1455", "detected_at": datetime.now(timezone.utc),
        "home_team_name": "Team A", "away_team_name": "Team B",
    }
    results = [_mock_result_for_mappings([row])]
    _patch_transaction_manager(context, results)


@given('a fake transaction manager returning 3 total and 2 won outcomes')
def step_summary_rows(context):
    results = [_mock_result_for_one(total=3, won=2)]
    _patch_transaction_manager(context, results)


@given('a fake transaction manager returning 1 insight row')
def step_one_insight_row(context):
    row = {
        "id": "i1", "match_id": "m1", "market": "match_result", "recommendation": "favorite:H",
        "confidence": "0.82", "rationale": "test", "model": "v4",
        "generated_at": datetime.now(timezone.utc),
        "home_team_name": "Team A", "away_team_name": "Team B",
    }
    results = [_mock_result_for_mappings([row])]
    _patch_transaction_manager(context, results)


@when('I get the overview')
def step_get_overview(context):
    with context.tm_patch:
        context.result = context.repo.get_overview()


@when(r'I list matches with limit (\d+) and offset (\d+)')
def step_list_matches(context, limit, offset):
    with context.tm_patch:
        context.result = context.repo.find_matches(limit=int(limit), offset=int(offset))


@when(r'I list value bets with limit (\d+) and offset (\d+)')
def step_list_value_bets(context, limit, offset):
    with context.tm_patch:
        context.result = context.repo.find_value_bets(limit=int(limit), offset=int(offset))


@when('I summarize value bet outcomes')
def step_summarize(context):
    with context.tm_patch:
        context.result = context.repo.summarize_value_bet_outcomes()


@when(r'I list insights with limit (\d+) and offset (\d+)')
def step_list_insights(context, limit, offset):
    with context.tm_patch:
        context.result = context.repo.find_insights(limit=int(limit), offset=int(offset))


@then(r'(\d+) overview rows? (?:is|are) returned')
def step_assert_overview_count(context, count):
    assert len(context.result) == int(count), len(context.result)


@then('the first overview row has a table name and a row count')
def step_assert_overview_shape(context):
    first = context.result[0]
    assert "table" in first and "rows" in first and "most_recent" in first, first


@then(r'(\d+) match dicts? (?:is|are) returned')
def step_assert_match_count(context, count):
    assert len(context.result) == int(count), len(context.result)


@then('the match dict has home and away team names')
def step_assert_match_team_names(context):
    row = context.result[0]
    assert row["home_team_name"] == "Team A", row
    assert row["away_team_name"] == "Team B", row


@then(r'(\d+) value bet dicts? (?:is|are) returned')
def step_assert_value_bet_count(context, count):
    assert len(context.result) == int(count), len(context.result)


@then(r'the summary reports (\d+) total, (\d+) won, (\d+) lost')
def step_assert_summary(context, total, won, lost):
    assert context.result["total"] == int(total), context.result
    assert context.result["won"] == int(won), context.result
    assert context.result["lost"] == int(lost), context.result


@then(r'(\d+) insight dicts? (?:is|are) returned')
def step_assert_insight_count(context, count):
    assert len(context.result) == int(count), len(context.result)
