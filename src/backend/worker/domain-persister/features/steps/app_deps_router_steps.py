from __future__ import annotations

import asyncio
import threading
from types import SimpleNamespace
from unittest.mock import Mock

from behave import given, then, use_step_matcher, when
from fastapi import HTTPException

from app.deps import _ready, get_read_models
from app.router import get_match, list_matches

use_step_matcher("re")


def _fake_request(**state_kwargs):
    return SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(**state_kwargs)))


@given('persister app state with init done and no error')
def step_state_ok(context):
    init_done = threading.Event()
    init_done.set()
    context.request = _fake_request(_init_done=init_done, _init_error=None, read_models="the-read-models")
    context.error = None


@given('persister app state with init done and an init error')
def step_state_error(context):
    init_done = threading.Event()
    init_done.set()
    context.request = _fake_request(_init_done=init_done, _init_error=RuntimeError("boom"))
    context.error = None


@when('I call persister _ready')
def step_call_ready(context):
    _ready(context.request)


@when('I call persister _ready expecting an error')
def step_call_ready_error(context):
    try:
        _ready(context.request)
    except HTTPException as e:
        context.error = e


@when('I call get_read_models')
def step_call_get_read_models(context):
    context.result = get_read_models(context.request)


@then('no exception is raised')
def step_no_exception(context):
    assert context.error is None


@then('a 503 HTTPException is raised')
def step_503(context):
    assert isinstance(context.error, HTTPException)
    assert context.error.status_code == 503


@then('it returns the read models object')
def step_assert_read_models(context):
    assert context.result == "the-read-models"


@given('a fake read model repository returning 1 match')
def step_fake_repo_list(context):
    context.repo = Mock()
    context.repo.find_all_matches.return_value = [{"match_id": "1"}]


@given('a fake read model repository with match "([^"]+)"')
def step_fake_repo_with_match(context, match_id):
    context.repo = Mock()
    context.repo.find_match.return_value = {"match_id": match_id}


@given('a fake read model repository with no matches')
def step_fake_repo_empty(context):
    context.repo = Mock()
    context.repo.find_match.return_value = None


@when('I call the list_matches endpoint')
def step_call_list_matches(context):
    context.result = list_matches(repo=context.repo)


@when('I call the get_match endpoint for "([^"]+)"')
def step_call_get_match(context, match_id):
    context.result = get_match(match_id, repo=context.repo)


@when('I call the get_match endpoint for "([^"]+)" expecting an error')
def step_call_get_match_error(context, match_id):
    try:
        get_match(match_id, repo=context.repo)
    except HTTPException as e:
        context.error = e


@then(r'(\d+) match(?:es)? (?:is|are) returned')
def step_assert_n_matches(context, count):
    assert len(context.result) == int(count)


@then('the match "([^"]+)" is returned')
def step_assert_match(context, match_id):
    assert context.result == {"match_id": match_id}


@then('a 404 HTTPException is raised')
def step_404(context):
    assert isinstance(context.error, HTTPException)
    assert context.error.status_code == 404
