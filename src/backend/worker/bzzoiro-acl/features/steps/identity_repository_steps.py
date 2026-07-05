from __future__ import annotations

from behave import given, then, use_step_matcher, when

from shared.transaction_manager import TransactionConfig, TransactionManager
from src.infrastructure.identity_repository import PostgresIdentityRepository
from src.infrastructure.models import Base

use_step_matcher("re")


@given('a fresh provider mapping table')
def step_fresh_table(context):
    TransactionManager.reset()
    TransactionManager.configure(TransactionConfig(url="sqlite:///:memory:"))
    Base.metadata.create_all(TransactionManager.get().engine)
    context.repo = PostgresIdentityRepository()
    context.canonical_id = None
    context.previous_canonical_id = None


@given(r'provider_ref "([^"]+)" of type "([^"]+)" was already resolved')
def step_already_resolved(context, provider_ref, entity_type):
    context.previous_canonical_id = context.repo.get_or_create("bzzoiro", provider_ref, entity_type)


@when(r'I resolve provider_ref "([^"]+)" of type "([^"]+)" for the first time')
def step_resolve_first(context, provider_ref, entity_type):
    context.canonical_id = context.repo.get_or_create("bzzoiro", provider_ref, entity_type)


@when(r'I resolve provider_ref "([^"]+)" of type "([^"]+)" again')
def step_resolve_again(context, provider_ref, entity_type):
    context.canonical_id = context.repo.get_or_create("bzzoiro", provider_ref, entity_type)


@when(r'I resolve provider_ref "([^"]+)" of type "([^"]+)"')
def step_resolve(context, provider_ref, entity_type):
    context.canonical_id = context.repo.get_or_create("bzzoiro", provider_ref, entity_type)


@then('a canonical UUID is returned')
def step_uuid_returned(context):
    assert context.canonical_id is not None


@then('the same canonical UUID is returned as before')
def step_same_uuid(context):
    assert context.canonical_id == context.previous_canonical_id, \
        f"expected {context.previous_canonical_id}, got {context.canonical_id}"


@then('a different canonical UUID is returned')
def step_different_uuid(context):
    assert context.canonical_id != context.previous_canonical_id, \
        "expected a different canonical id for a different entity_type"
