from decimal import Decimal
from typing import Optional

from behave import given, then, use_step_matcher, when

from src.application.commands.delete_transaction import DeleteTransactionCommand, DeleteTransactionHandler
from src.application.commands.record_transaction import RecordTransactionCommand, RecordTransactionHandler
from src.application.commands.update_transaction import UpdateTransactionCommand, UpdateTransactionHandler
from src.application.queries.get_summary import GetSummaryHandler, GetSummaryQuery
from src.domain.events import TransactionDeleted, TransactionRecorded
from src.domain.repository import TransactionRepository
from src.domain.transaction import Transaction
from src.infrastructure.event_bus import EventBus

use_step_matcher("re")


class InMemoryTransactionRepository(TransactionRepository):
    def __init__(self):
        self._store: dict[str, Transaction] = {}

    def save(self, transaction: Transaction) -> None:
        self._store[transaction.id] = transaction

    def delete(self, transaction_id: str) -> bool:
        if transaction_id in self._store:
            del self._store[transaction_id]
            return True
        return False

    def find_all(self, limit=50, offset=0, month=None, year=None) -> list[Transaction]:
        transactions = list(self._store.values())
        if month is not None:
            transactions = [t for t in transactions if t.date.month == month]
        if year is not None:
            transactions = [t for t in transactions if t.date.year == year]
        return transactions[offset:offset + limit]

    def find_by_id(self, transaction_id: str) -> Optional[Transaction]:
        return self._store.get(transaction_id)


def _setup_context(context):
    context.repo = InMemoryTransactionRepository()
    context.bus = EventBus()
    context.published_events = []
    context.bus.subscribe(TransactionRecorded, lambda e: context.published_events.append(e))
    context.bus.subscribe(TransactionDeleted, lambda e: context.published_events.append(e))
    context.record_handler = RecordTransactionHandler(context.repo, context.bus)
    context.update_handler = UpdateTransactionHandler(context.repo, context.bus)
    context.delete_handler = DeleteTransactionHandler(context.repo, context.bus)
    context.summary_handler = GetSummaryHandler(context.repo)
    context.last_transaction = None
    context.last_error = None
    context.last_result = None


# Given

@given('an empty transaction repository')
def step_empty_repo(context):
    _setup_context(context)


# "I have recorded on <date>" prefix avoids ambiguity with the no-date variant below
@given(r'I have recorded on "([^"]+)" an income of "([^"]+)" in category "([^"]+)" described as "([^"]+)"')
def step_given_income_on_date(context, date, amount, category, description):
    cmd = RecordTransactionCommand(amount=amount, type="income", category=category, description=description, date=date)
    context.last_transaction = context.record_handler.handle(cmd)


@given(r'I have recorded on "([^"]+)" an expense of "([^"]+)" in category "([^"]+)" described as "([^"]+)"')
def step_given_expense_on_date(context, date, amount, category, description):
    cmd = RecordTransactionCommand(amount=amount, type="expense", category=category, description=description, date=date)
    context.last_transaction = context.record_handler.handle(cmd)


@given(r'I have recorded an income of "([^"]+)" in category "([^"]+)" described as "([^"]+)"')
def step_given_income(context, amount, category, description):
    cmd = RecordTransactionCommand(amount=amount, type="income", category=category, description=description)
    context.last_transaction = context.record_handler.handle(cmd)


@given(r'I have recorded an expense of "([^"]+)" in category "([^"]+)" described as "([^"]+)"')
def step_given_expense(context, amount, category, description):
    cmd = RecordTransactionCommand(amount=amount, type="expense", category=category, description=description)
    context.last_transaction = context.record_handler.handle(cmd)


# When: record

@when(r'I record an income of "([^"]+)" in category "([^"]+)" described as "([^"]+)"')
def step_record_income(context, amount, category, description):
    cmd = RecordTransactionCommand(amount=amount, type="income", category=category, description=description)
    context.last_transaction = context.record_handler.handle(cmd)
    context.last_error = None


@when(r'I record an expense of "([^"]+)" in category "([^"]+)" described as "([^"]+)"')
def step_record_expense(context, amount, category, description):
    cmd = RecordTransactionCommand(amount=amount, type="expense", category=category, description=description)
    context.last_transaction = context.record_handler.handle(cmd)
    context.last_error = None


@when(r'I try to record an income of "([^"]+)" in category "([^"]*)" described as "([^"]*)"')
def step_try_record_income(context, amount, category, description):
    cmd = RecordTransactionCommand(amount=amount, type="income", category=category, description=description)
    try:
        context.record_handler.handle(cmd)
        context.last_error = None
    except Exception as e:
        context.last_error = e


@when(r'I try to record a "([^"]+)" of "([^"]+)" in category "([^"]+)" described as "([^"]+)"')
def step_try_record_type(context, t_type, amount, category, description):
    cmd = RecordTransactionCommand(amount=amount, type=t_type, category=category, description=description)
    try:
        context.record_handler.handle(cmd)
        context.last_error = None
    except Exception as e:
        context.last_error = e


# When: update

@when(r'I update the transaction with amount "([^"]+)" type "([^"]+)" category "([^"]+)" description "([^"]+)"')
def step_update_transaction(context, amount, t_type, category, description):
    assert context.last_transaction is not None, "No transaction recorded in Background"
    cmd = UpdateTransactionCommand(
        transaction_id=context.last_transaction.id,
        amount=amount,
        type=t_type,
        category=category,
        description=description,
    )
    context.last_result = context.update_handler.handle(cmd)
    context.last_error = None


@when(r'I update transaction "([^"]+)" with amount "([^"]+)" type "([^"]+)" category "([^"]+)" description "([^"]+)"')
def step_update_transaction_by_id(context, transaction_id, amount, t_type, category, description):
    cmd = UpdateTransactionCommand(
        transaction_id=transaction_id,
        amount=amount,
        type=t_type,
        category=category,
        description=description,
    )
    context.last_result = context.update_handler.handle(cmd)
    context.last_error = None


@when(r'I try to update the transaction with amount "([^"]+)" type "([^"]+)" category "([^"]+)" description "([^"]+)"')
def step_try_update_transaction(context, amount, t_type, category, description):
    assert context.last_transaction is not None, "No transaction recorded in Background"
    cmd = UpdateTransactionCommand(
        transaction_id=context.last_transaction.id,
        amount=amount,
        type=t_type,
        category=category,
        description=description,
    )
    try:
        context.update_handler.handle(cmd)
        context.last_error = None
    except Exception as e:
        context.last_error = e


# When: delete

@when(r'I delete the last recorded transaction')
def step_delete_last(context):
    assert context.last_transaction is not None, "No transaction recorded in Background"
    cmd = DeleteTransactionCommand(transaction_id=context.last_transaction.id)
    context.last_result = context.delete_handler.handle(cmd)


@when(r'I delete transaction "([^"]+)"')
def step_delete_by_id(context, transaction_id):
    cmd = DeleteTransactionCommand(transaction_id=transaction_id)
    context.last_result = context.delete_handler.handle(cmd)


# When: queries

@when(r'I request the summary')
def step_request_summary(context):
    context.last_result = context.summary_handler.handle(GetSummaryQuery())


@when(r'I request the summary for month (\d+) of year (\d+)')
def step_request_summary_filtered(context, month, year):
    context.last_result = context.summary_handler.handle(GetSummaryQuery(month=int(month), year=int(year)))


# Then

@then(r'(\d+) transactions? (?:is|are) saved')
def step_n_transactions_saved(context, count):
    all_txns = context.repo.find_all(limit=10_000)
    assert len(all_txns) == int(count), f"Expected {count} transaction(s), got {len(all_txns)}"


@then(r'the transaction type is "([^"]+)"')
def step_transaction_type(context, expected_type):
    assert context.last_transaction is not None
    actual = context.last_transaction.type.value
    assert actual == expected_type, f"Expected type '{expected_type}', got '{actual}'"


@then(r'the transaction amount is "([^"]+)"')
def step_transaction_amount(context, expected_amount):
    assert context.last_transaction is not None
    actual = context.last_transaction.amount.amount
    assert actual == Decimal(expected_amount), f"Expected amount {expected_amount}, got {actual}"


@then(r'a TransactionRecorded event is published')
def step_event_recorded(context):
    recorded = [e for e in context.published_events if isinstance(e, TransactionRecorded)]
    assert recorded, f"Expected TransactionRecorded event; published: {context.published_events}"


@then(r'a TransactionDeleted event is published')
def step_event_deleted(context):
    deleted = [e for e in context.published_events if isinstance(e, TransactionDeleted)]
    assert deleted, f"Expected TransactionDeleted event; published: {context.published_events}"


@then(r'no TransactionDeleted event is published')
def step_no_event_deleted(context):
    deleted = [e for e in context.published_events if isinstance(e, TransactionDeleted)]
    assert not deleted, f"Expected no TransactionDeleted event, got: {deleted}"


@then(r'a validation error contains "([^"]+)"')
def step_validation_error(context, message):
    assert context.last_error is not None, "Expected a validation error but none was raised"
    error_str = str(context.last_error)
    assert message in error_str, f"Expected '{message}' in error, got: {error_str}"


@then(r'the repository is empty')
def step_repo_empty(context):
    all_txns = context.repo.find_all(limit=10_000)
    assert not all_txns, f"Expected empty repository, got {len(all_txns)} transaction(s)"


@then(r'the deletion returns false')
def step_deletion_false(context):
    assert context.last_result is False, f"Expected False, got {context.last_result}"


@then(r'no update is performed')
def step_no_update(context):
    assert context.last_result is None, f"Expected None for missing transaction, got {context.last_result}"


@then(r'a reversal transaction of "([^"]+)" exists')
def step_reversal_exists(context, amount):
    expected = Decimal(amount)
    all_txns = context.repo.find_all(limit=10_000)
    amounts = [str(t.amount.amount) for t in all_txns]
    assert any(t.amount.amount == expected for t in all_txns), \
        f"No transaction with amount {amount} found. Amounts: {amounts}"


@then(r'a new transaction of "([^"]+)" with type "([^"]+)" exists')
def step_new_transaction_with_type(context, amount, expected_type):
    expected_amount = Decimal(amount)
    all_txns = context.repo.find_all(limit=10_000)
    match = any(t.amount.amount == expected_amount and t.type.value == expected_type for t in all_txns)
    assert match, f"No {expected_type} transaction with amount {amount} found"


@then(r'a new transaction of "([^"]+)" exists')
def step_new_transaction_exists(context, amount):
    expected = Decimal(amount)
    all_txns = context.repo.find_all(limit=10_000)
    amounts = [str(t.amount.amount) for t in all_txns]
    assert any(t.amount.amount == expected for t in all_txns), \
        f"No transaction with amount {amount} found. Amounts: {amounts}"


@then(r'the total income is "([^"]+)"')
def step_total_income(context, expected):
    assert context.last_result is not None
    assert context.last_result.total_income == Decimal(expected), \
        f"Expected income {expected}, got {context.last_result.total_income}"


@then(r'the total expenses are "([^"]+)"')
def step_total_expenses(context, expected):
    assert context.last_result is not None
    assert context.last_result.total_expenses == Decimal(expected), \
        f"Expected expenses {expected}, got {context.last_result.total_expenses}"


@then(r'the balance is "([^"]+)"')
def step_balance(context, expected):
    assert context.last_result is not None
    assert context.last_result.balance == Decimal(expected), \
        f"Expected balance {expected}, got {context.last_result.balance}"


@then(r'the transaction count is (\d+)')
def step_transaction_count(context, count):
    assert context.last_result is not None
    assert context.last_result.transaction_count == int(count), \
        f"Expected count {count}, got {context.last_result.transaction_count}"
