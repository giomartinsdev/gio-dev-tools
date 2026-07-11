from __future__ import annotations

from contextlib import contextmanager
from unittest.mock import Mock, patch

from behave import given, then, use_step_matcher, when

from src.infrastructure.config_repository import ConfigRepository
from src.infrastructure.recipients_repository import RecipientsRepository

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


@given('a fake transaction manager returning a config row')
def step_fake_tm_config(context):
    context.row = Mock(send_time="00:00", reference_day_offset=1, enabled=True)
    context.session = Mock()
    context.session.get.return_value = context.row
    context.repo = ConfigRepository()
    fake_tm = _FakeTransactionManager(context.session)
    tm_patch = patch(
        "src.infrastructure.config_repository.TransactionManager.get", return_value=fake_tm,
    )
    tm_patch.start()
    context.add_cleanup(tm_patch.stop)


@when('I get the config')
def step_get_config(context):
    context.result = context.repo.get()


@when(r'I update the config to send_time "([^"]+)", offset (\d+), enabled (true|false)')
def step_update_config(context, send_time, offset, enabled):
    context.result = context.repo.update(send_time, int(offset), enabled == "true")


@then('the config has send_time "([^"]+)"')
def step_assert_config_send_time(context, send_time):
    assert context.result.send_time == send_time, context.result


@then('the row was updated with send_time "([^"]+)"')
def step_assert_row_updated(context, send_time):
    assert context.row.send_time == send_time, context.row.send_time
    assert context.result.send_time == send_time, context.result


def _recipient_row(id_, phone, name, active):
    row = Mock()
    row.id = id_
    row.phone_number = phone
    row.name = name
    row.active = active
    return row


@given('a fake transaction manager for recipients')
def step_fake_tm_recipients(context):
    context.session = Mock()
    context.repo = RecipientsRepository()
    fake_tm = _FakeTransactionManager(context.session)
    tm_patch = patch(
        "src.infrastructure.recipients_repository.TransactionManager.get", return_value=fake_tm,
    )
    tm_patch.start()
    context.add_cleanup(tm_patch.stop)


@given(r'a fake transaction manager listing (\d+) active and (\d+) inactive recipients?')
def step_fake_tm_recipients_list(context, active_count, inactive_count):
    context.session = Mock()
    rows = (
        [_recipient_row(i, f"5511{i:09d}", None, True) for i in range(int(active_count))]
        + [_recipient_row(100 + i, f"5522{i:09d}", None, False) for i in range(int(inactive_count))]
    )
    context.session.query.return_value.filter.return_value.all.return_value = [r for r in rows if r.active]
    context.session.query.return_value.order_by.return_value.all.return_value = rows
    context.repo = RecipientsRepository()
    fake_tm = _FakeTransactionManager(context.session)
    tm_patch = patch(
        "src.infrastructure.recipients_repository.TransactionManager.get", return_value=fake_tm,
    )
    tm_patch.start()
    context.add_cleanup(tm_patch.stop)


@given('a fake transaction manager with no matching recipient row')
def step_fake_tm_recipients_missing(context):
    context.session = Mock()
    context.session.get.return_value = None
    context.repo = RecipientsRepository()
    fake_tm = _FakeTransactionManager(context.session)
    tm_patch = patch(
        "src.infrastructure.recipients_repository.TransactionManager.get", return_value=fake_tm,
    )
    tm_patch.start()
    context.add_cleanup(tm_patch.stop)


@when(r'I create a recipient with phone "([^"]+)" and name "([^"]+)"')
def step_create_recipient(context, phone, name):
    context.result = context.repo.create(phone, name)


@when('I list active recipients')
def step_list_active(context):
    context.result = context.repo.list_active()


@when('I list all recipients')
def step_list_all(context):
    context.result = context.repo.list_all()


@when(r'I delete recipient (\d+)')
def step_delete_recipient(context, recipient_id):
    context.repo.delete(int(recipient_id))


@when(r'I set active for recipient (\d+)')
def step_set_active(context, recipient_id):
    context.result = context.repo.set_active(int(recipient_id), False)


@then('a recipient row was added')
def step_assert_row_added(context):
    context.session.add.assert_called_once()


@then(r'1 active recipients? is returned')
def step_assert_one_active(context):
    assert len(context.result) == 1, context.result
    assert context.result[0].active is True, context.result


@then(r'a delete was issued for recipient (\d+)')
def step_assert_delete_issued(context, recipient_id):
    context.session.query.return_value.filter.return_value.delete.assert_called_once()


@then('the result is empty')
def step_assert_result_empty(context):
    assert context.result is None, context.result
