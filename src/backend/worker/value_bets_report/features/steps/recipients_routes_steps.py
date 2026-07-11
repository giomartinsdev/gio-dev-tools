from __future__ import annotations

from unittest.mock import Mock

from behave import given, then, use_step_matcher, when
from fastapi import HTTPException

from app.router import (
    RecipientCreate,
    RecipientUpdate,
    create_recipient,
    delete_recipient,
    list_recipients,
    update_recipient,
)
from src.infrastructure.recipients_repository import Recipient

use_step_matcher("re")


@given('a recipients repository')
def step_repo(context):
    context.repo = Mock()
    context.error = None


@given(r'a recipients repository returning (\d+) recipients?')
def step_repo_list(context, count):
    context.repo = Mock()
    context.repo.list_all.return_value = [
        Recipient(id=i, phone_number=f"55119999999{i:02d}", name=None, active=True) for i in range(int(count))
    ]


@given(r'a recipients repository that can toggle recipient (\d+)')
def step_repo_toggle(context, recipient_id):
    context.repo = Mock()

    def _set_active(rid, active):
        return Recipient(id=rid, phone_number="5511999999999", name=None, active=active)

    context.repo.set_active.side_effect = _set_active


@given('a recipients repository with no matching recipient')
def step_repo_missing(context):
    context.repo = Mock()
    context.repo.set_active.return_value = None
    context.error = None


@when(r'I call the create_recipient endpoint with phone "([^"]+)" and name "([^"]+)"')
def step_call_create(context, phone, name):
    context.result = create_recipient(RecipientCreate(phone_number=phone, name=name), repo=context.repo)


@when('I call the list_recipients endpoint')
def step_call_list(context):
    context.result = list_recipients(repo=context.repo)


@when(r'I call the update_recipient endpoint for id (\d+) with active (true|false)')
def step_call_update(context, recipient_id, active):
    context.result = update_recipient(int(recipient_id), RecipientUpdate(active=(active == "true")), repo=context.repo)


@when(r'I call the update_recipient endpoint for id (\d+) with active (true|false) expecting an error')
def step_call_update_error(context, recipient_id, active):
    try:
        update_recipient(int(recipient_id), RecipientUpdate(active=(active == "true")), repo=context.repo)
    except HTTPException as e:
        context.error = e


@when(r'I call the delete_recipient endpoint for id (\d+)')
def step_call_delete(context, recipient_id):
    context.result = delete_recipient(int(recipient_id), repo=context.repo)


@then(r'the repository created a recipient with phone "([^"]+)" and name "([^"]+)"')
def step_assert_created(context, phone, name):
    context.repo.create.assert_called_once_with(phone_number=phone, name=name)


@then(r'(\d+) recipients? are returned')
def step_assert_count(context, count):
    assert len(context.result) == int(count), context.result


@then('the returned recipient is inactive')
def step_assert_inactive(context):
    assert context.result.active is False, context.result


@then('a 404 HTTPException is raised')
def step_assert_404(context):
    assert isinstance(context.error, HTTPException)
    assert context.error.status_code == 404


@then(r'the repository deleted recipient (\d+)')
def step_assert_deleted(context, recipient_id):
    context.repo.delete.assert_called_once_with(int(recipient_id))
