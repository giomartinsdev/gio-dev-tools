from behave import given, then, use_step_matcher, when

from src.application.commands.create_tracked_line import CreateTrackedLineCommand, CreateTrackedLineHandler
from src.application.commands.delete_tracked_line import DeleteTrackedLineCommand, DeleteTrackedLineHandler
from src.application.commands.update_tracked_line import UpdateTrackedLineCommand, UpdateTrackedLineHandler
from src.domain.events import TrackedLineCreated, TrackedLineDeleted, TrackedLineUpdated
from src.infrastructure.event_bus import EventBus
from src.infrastructure.tracked_line_repository import PostgresTrackedLineRepository

use_step_matcher("re")


def _setup(context):
    context.repo = PostgresTrackedLineRepository()
    context.bus = EventBus()
    context.published_events = []
    for event_type in (TrackedLineCreated, TrackedLineUpdated, TrackedLineDeleted):
        context.bus.subscribe(event_type, lambda e: context.published_events.append(e))
    context.create_handler = CreateTrackedLineHandler(context.repo, context.bus)
    context.update_handler = UpdateTrackedLineHandler(context.repo, context.bus)
    context.delete_handler = DeleteTrackedLineHandler(context.repo, context.bus)
    context.last_line = None
    context.last_result = None
    context.last_error = None


@given("an empty tracked line repository")
def step_empty_repo(context):
    _setup(context)


@given(r'a tracked line with code "([^"]+)" exists')
def step_line_exists(context, line_code):
    _setup(context)
    context.last_line = context.create_handler.handle(CreateTrackedLineCommand(line_code=line_code))
    context.published_events.clear()


@when(r'I create a tracked line with code "([^"]*)" label "([^"]*)"')
def step_create_line_with_label(context, line_code, label):
    context.last_line = context.create_handler.handle(
        CreateTrackedLineCommand(line_code=line_code, label=label)
    )
    context.last_error = None


@when(r'I try to create a tracked line with code "([^"]*)"')
def step_try_create_line(context, line_code):
    try:
        context.create_handler.handle(CreateTrackedLineCommand(line_code=line_code))
        context.last_error = None
    except Exception as e:
        context.last_error = e


@when(r'I update the line to code "([^"]+)" label "([^"]*)" active "([^"]+)"')
def step_update_line(context, line_code, label, active):
    context.last_line = context.update_handler.handle(UpdateTrackedLineCommand(
        line_id=context.last_line.id, line_code=line_code, label=label, active=active.lower() == "true",
    ))
    context.last_error = None


@when(r'I try to update line "([^"]+)" to code "([^"]+)"')
def step_try_update_missing_line(context, line_id, line_code):
    context.last_line = context.update_handler.handle(
        UpdateTrackedLineCommand(line_id=line_id, line_code=line_code)
    )


@when("I delete the line")
def step_delete_line(context):
    context.last_result = context.delete_handler.handle(DeleteTrackedLineCommand(line_id=context.last_line.id))


@when(r'I try to delete line "([^"]+)"')
def step_try_delete_missing_line(context, line_id):
    context.last_result = context.delete_handler.handle(DeleteTrackedLineCommand(line_id=line_id))


@then(r'the tracked line is saved with code "([^"]+)" and label "([^"]*)"')
def step_line_saved(context, line_code, label):
    assert context.last_line is not None
    assert context.last_line.line_code == line_code, \
        f"Expected line_code {line_code!r}, got {context.last_line.line_code!r}"
    assert context.last_line.label == label, f"Expected label {label!r}, got {context.last_line.label!r}"


@then("the tracked line is inactive")
def step_line_inactive(context):
    assert context.last_line.active is False, "Expected line to be inactive"


@then("no line is returned")
def step_no_line_returned(context):
    assert context.last_line is None, f"Expected None, got {context.last_line}"


@then("the tracked line repository is empty")
def step_repo_empty(context):
    assert not context.repo.find_all(), "Expected empty tracked line repository"


@then("the deletion returns false")
def step_deletion_false(context):
    assert context.last_result is False, f"Expected False, got {context.last_result}"


@then(r'a TrackedLineCreated event is published')
def step_created_event(context):
    events = [e for e in context.published_events if isinstance(e, TrackedLineCreated)]
    assert events, f"Expected TrackedLineCreated event; got: {context.published_events}"


@then(r'a validation error contains "([^"]+)"')
def step_validation_error(context, message):
    assert context.last_error is not None, "Expected a validation error but none was raised"
    assert message in str(context.last_error), f"Expected '{message}' in error: {context.last_error}"
