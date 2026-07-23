from typing import Optional

from behave import given, then, use_step_matcher, when

from src.application.commands.create_service import CreateServiceCommand, CreateServiceHandler
from src.application.commands.delete_service import DeleteServiceCommand, DeleteServiceHandler
from src.application.commands.update_service import UpdateServiceCommand, UpdateServiceHandler
from src.domain.service import Service
from src.domain.events import ServiceCreated, ServiceDeleted, ServiceUpdated
from src.domain.repository import ServiceRepository
from src.infrastructure.event_bus import EventBus

use_step_matcher("re")


class InMemoryServiceRepository(ServiceRepository):
    def __init__(self):
        self._store: dict[str, Service] = {}

    def save(self, service: Service) -> None:
        self._store[service.id] = service

    def update(self, service: Service) -> None:
        if service.id in self._store:
            self._store[service.id] = service

    def delete(self, service_id: str) -> bool:
        if service_id in self._store:
            del self._store[service_id]
            return True
        return False

    def find_all(self) -> list[Service]:
        return list(self._store.values())

    def find_by_id(self, service_id: str) -> Optional[Service]:
        return self._store.get(service_id)


def _setup(context):
    context.repo = InMemoryServiceRepository()
    context.bus = EventBus()
    context.published_events = []
    for event_type in (ServiceCreated, ServiceUpdated, ServiceDeleted):
        context.bus.subscribe(event_type, lambda e: context.published_events.append(e))
    context.create_handler = CreateServiceHandler(context.repo, context.bus)
    context.update_handler = UpdateServiceHandler(context.repo, context.bus)
    context.delete_handler = DeleteServiceHandler(context.repo, context.bus)
    context.last_service = None
    context.last_result = None
    context.last_error = None


# Given

@given('an empty service repository')
def step_empty_repo(context):
    _setup(context)


@given(r'a service named "([^"]+)" category "([^"]+)" exists')
def step_service_exists(context, name, category):
    context.last_service = context.create_handler.handle(
        CreateServiceCommand(name=name, category=category)
    )
    context.published_events.clear()


# When — create

@when(r'I create a service named "([^"]+)" category "([^"]+)" secret ref "([^"]+)"')
def step_create_service_with_ref(context, name, category, secret_ref):
    context.last_service = context.create_handler.handle(
        CreateServiceCommand(name=name, category=category, secret_ref=secret_ref)
    )
    context.last_error = None


@when(r'I try to create a service named "([^"]*)" category "([^"]*)" status "([^"]*)"')
def step_try_create_service_with_status(context, name, category, status):
    try:
        context.create_handler.handle(CreateServiceCommand(name=name, category=category, status=status))
        context.last_error = None
    except Exception as e:
        context.last_error = e


# When — update

@when(r'I update the service with name "([^"]+)" category "([^"]+)" status "([^"]+)"')
def step_update_service(context, name, category, status):
    context.last_service = context.update_handler.handle(
        UpdateServiceCommand(service_id=context.last_service.id, name=name, category=category, status=status)
    )
    context.last_error = None


@when(r'I try to update the service with name "([^"]*)" category "([^"]*)" status "([^"]*)"')
def step_try_update_service(context, name, category, status):
    try:
        context.update_handler.handle(
            UpdateServiceCommand(service_id=context.last_service.id, name=name, category=category, status=status)
        )
        context.last_error = None
    except Exception as e:
        context.last_error = e


@when(r'I update service "([^"]+)" with name "([^"]+)" category "([^"]+)" status "([^"]+)"')
def step_update_service_by_id(context, service_id, name, category, status):
    context.last_result = context.update_handler.handle(
        UpdateServiceCommand(service_id=service_id, name=name, category=category, status=status)
    )


# When — delete

@when(r'I delete the service')
def step_delete_service(context):
    context.last_result = context.delete_handler.handle(DeleteServiceCommand(service_id=context.last_service.id))


@when(r'I delete service "([^"]+)"')
def step_delete_service_by_id(context, service_id):
    context.last_result = context.delete_handler.handle(DeleteServiceCommand(service_id=service_id))


# Then

@then(r'the service is saved with name "([^"]+)" and category "([^"]+)"')
def step_service_saved(context, name, category):
    assert context.last_service is not None
    assert context.last_service.name == name, f"Expected name '{name}', got '{context.last_service.name}'"
    assert context.last_service.category.value == category, \
        f"Expected category '{category}', got '{context.last_service.category.value}'"


@then(r'the service repository has (\d+) service')
def step_repo_count(context, count):
    services = context.repo.find_all()
    assert len(services) == int(count), f"Expected {count} service(s), got {len(services)}"


@then(r'the service has name "([^"]+)" and status "([^"]+)"')
def step_service_fields(context, name, status):
    assert context.last_service is not None
    assert context.last_service.name == name, f"Expected name '{name}', got '{context.last_service.name}'"
    assert context.last_service.status.value == status, \
        f"Expected status '{status}', got '{context.last_service.status.value}'"


@then(r'the service repository is empty')
def step_repo_empty(context):
    assert not context.repo.find_all(), "Expected empty service repository"


@then(r'a ServiceCreated event is published')
def step_service_created_event(context):
    events = [e for e in context.published_events if isinstance(e, ServiceCreated)]
    assert events, f"Expected ServiceCreated event; got: {context.published_events}"


@then(r'a ServiceUpdated event is published')
def step_service_updated_event(context):
    events = [e for e in context.published_events if isinstance(e, ServiceUpdated)]
    assert events, f"Expected ServiceUpdated event; got: {context.published_events}"


@then(r'a ServiceDeleted event is published')
def step_service_deleted_event(context):
    events = [e for e in context.published_events if isinstance(e, ServiceDeleted)]
    assert events, f"Expected ServiceDeleted event; got: {context.published_events}"


@then(r'a validation error contains "([^"]+)"')
def step_validation_error(context, message):
    assert context.last_error is not None, "Expected a validation error but none was raised"
    assert message in str(context.last_error), f"Expected '{message}' in error: {context.last_error}"


@then(r'the deletion returns false')
def step_deletion_false(context):
    assert context.last_result is False, f"Expected False, got {context.last_result}"


@then(r'no update is performed')
def step_no_update(context):
    assert context.last_result is None, f"Expected None, got {context.last_result}"
