from __future__ import annotations

from unittest.mock import Mock

from behave import given, then, use_step_matcher, when

from src.application.queries.get_match import GetMatchHandler, GetMatchQuery
from src.application.queries.list_matches import ListMatchesHandler, ListMatchesQuery

use_step_matcher("re")


@given('a fake read model repository')
def step_fake_repo(context):
    context.repo = Mock()
    context.repo.find_all_matches.return_value = [{"match_id": "1"}]
    context.repo.find_match.return_value = {"match_id": "abc-123"}


@when(r'I list matches with limit (\d+) and offset (\d+)')
def step_list_matches(context, limit, offset):
    context.result = ListMatchesHandler(context.repo).handle(
        ListMatchesQuery(limit=int(limit), offset=int(offset))
    )


@when(r'I get match "([^"]+)"')
def step_get_match(context, match_id):
    context.result = GetMatchHandler(context.repo).handle(GetMatchQuery(match_id=match_id))


@then(r'find_all_matches was called with limit (\d+) and offset (\d+)')
def step_assert_find_all(context, limit, offset):
    context.repo.find_all_matches.assert_called_once_with(limit=int(limit), offset=int(offset))


@then(r'find_match was called with "([^"]+)"')
def step_assert_find_match(context, match_id):
    context.repo.find_match.assert_called_once_with(match_id)
