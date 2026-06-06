from typing import Optional

from behave import given, then, use_step_matcher, when

from src.application.commands.create_board import CreateBoardCommand, CreateBoardHandler
from src.application.commands.create_card import CreateCardCommand, CreateCardHandler
from src.application.commands.delete_board import DeleteBoardCommand, DeleteBoardHandler
from src.application.commands.delete_card import DeleteCardCommand, DeleteCardHandler
from src.application.commands.update_card import UpdateCardCommand, UpdateCardHandler
from src.domain.board import Board
from src.domain.card import Card
from src.domain.events import BoardCreated, BoardDeleted, CardCreated, CardDeleted, CardUpdated
from src.domain.repository import BoardRepository, CardRepository
from src.infrastructure.event_bus import EventBus

use_step_matcher("re")


class InMemoryBoardRepository(BoardRepository):
    def __init__(self):
        self._store: dict[str, Board] = {}

    def save(self, board: Board) -> None:
        self._store[board.id] = board

    def find_all(self) -> list[Board]:
        return list(self._store.values())

    def find_by_id(self, board_id: str) -> Optional[Board]:
        return self._store.get(board_id)

    def delete(self, board_id: str) -> bool:
        if board_id in self._store:
            del self._store[board_id]
            return True
        return False


class InMemoryCardRepository(CardRepository):
    def __init__(self):
        self._store: dict[str, Card] = {}

    def save(self, card: Card) -> None:
        self._store[card.id] = card

    def find_by_board(self, board_id: str) -> list[Card]:
        return [c for c in self._store.values() if c.board_id == board_id]

    def find_by_id(self, card_id: str) -> Optional[Card]:
        return self._store.get(card_id)

    def delete(self, card_id: str) -> bool:
        if card_id in self._store:
            del self._store[card_id]
            return True
        return False


def _setup(context):
    context.bus = EventBus()
    context.published_events = []
    for event_type in (BoardCreated, BoardDeleted, CardCreated, CardUpdated, CardDeleted):
        context.bus.subscribe(event_type, lambda e: context.published_events.append(e))
    context.last_board = None
    context.last_card = None
    context.last_result = None
    context.last_error = None


# Given

@given('an empty board repository')
def step_empty_board_repo(context):
    _setup(context)
    context.board_repo = InMemoryBoardRepository()
    context.board_handler = CreateBoardHandler(context.board_repo, context.bus)
    context.delete_board_handler = DeleteBoardHandler(context.board_repo, context.bus)


@given('an empty card repository')
def step_empty_card_repo(context):
    context.card_repo = InMemoryCardRepository()
    context.card_handler = CreateCardHandler(context.card_repo, context.bus)
    context.update_card_handler = UpdateCardHandler(context.card_repo, context.bus)
    context.delete_card_handler = DeleteCardHandler(context.card_repo, context.bus)


@given(r'a board named "([^"]+)" exists')
def step_board_exists(context, name):
    context.last_board = context.board_handler.handle(CreateBoardCommand(name=name))
    context.published_events.clear()


@given(r'a card with title "([^"]+)" status "([^"]+)" exists in the board')
def step_card_exists(context, title, status):
    context.last_card = context.card_handler.handle(
        CreateCardCommand(board_id=context.last_board.id, title=title, status=status)
    )
    context.published_events.clear()


# When — boards

@when(r'I create a board named "([^"]*)"')
def step_create_board(context, name):
    context.last_board = context.board_handler.handle(CreateBoardCommand(name=name))
    context.last_error = None


@when(r'I try to create a board named "([^"]*)"')
def step_try_create_board(context, name):
    try:
        context.board_handler.handle(CreateBoardCommand(name=name))
        context.last_error = None
    except Exception as e:
        context.last_error = e


@when(r'I delete the board')
def step_delete_board(context):
    context.last_result = context.delete_board_handler.handle(
        DeleteBoardCommand(board_id=context.last_board.id)
    )


@when(r'I delete board "([^"]+)"')
def step_delete_board_by_id(context, board_id):
    context.last_result = context.delete_board_handler.handle(DeleteBoardCommand(board_id=board_id))


# When — cards

@when(r'I create a card with title "([^"]*)" status "([^"]*)" in the board')
def step_create_card(context, title, status):
    context.last_card = context.card_handler.handle(
        CreateCardCommand(board_id=context.last_board.id, title=title, status=status)
    )
    context.last_error = None


@when(r'I try to create a card with title "([^"]*)" status "([^"]*)" in the board')
def step_try_create_card(context, title, status):
    try:
        context.card_handler.handle(
            CreateCardCommand(board_id=context.last_board.id, title=title, status=status)
        )
        context.last_error = None
    except Exception as e:
        context.last_error = e


@when(r'I update the card with title "([^"]*)" status "([^"]*)"')
def step_update_card(context, title, status):
    context.last_result = context.update_card_handler.handle(
        UpdateCardCommand(
            card_id=context.last_card.id,
            title=title,
            content=context.last_card.content,
            status=status,
            board_id=context.last_card.board_id,
        )
    )
    context.last_error = None


@when(r'I try to update the card with title "([^"]*)" status "([^"]*)"')
def step_try_update_card(context, title, status):
    try:
        context.update_card_handler.handle(
            UpdateCardCommand(
                card_id=context.last_card.id,
                title=title,
                content="",
                status=status,
                board_id=context.last_card.board_id,
            )
        )
        context.last_error = None
    except Exception as e:
        context.last_error = e


@when(r'I update card "([^"]+)" with title "([^"]*)" status "([^"]*)"')
def step_update_card_by_id(context, card_id, title, status):
    context.last_result = context.update_card_handler.handle(
        UpdateCardCommand(card_id=card_id, title=title, content="", status=status, board_id="")
    )


@when(r'I delete the card')
def step_delete_card(context):
    context.last_result = context.delete_card_handler.handle(
        DeleteCardCommand(card_id=context.last_card.id)
    )


@when(r'I delete card "([^"]+)"')
def step_delete_card_by_id(context, card_id):
    context.last_result = context.delete_card_handler.handle(DeleteCardCommand(card_id=card_id))


# Then

@then(r'the board is saved with name "([^"]+)"')
def step_board_saved(context, name):
    boards = context.board_repo.find_all()
    assert any(b.name == name for b in boards), f"No board with name '{name}': {[b.name for b in boards]}"


@then(r'the board repository is empty')
def step_board_repo_empty(context):
    assert not context.board_repo.find_all(), "Expected empty board repository"


@then(r'the card is saved with title "([^"]+)" and status "([^"]+)"')
def step_card_saved(context, title, status):
    assert context.last_card is not None
    assert context.last_card.title == title, f"Expected title '{title}', got '{context.last_card.title}'"
    assert context.last_card.status.value == status, f"Expected status '{status}', got '{context.last_card.status.value}'"


@then(r'the card has title "([^"]+)" and status "([^"]+)"')
def step_card_updated(context, title, status):
    card = context.last_result
    assert card is not None
    assert card.title == title, f"Expected title '{title}', got '{card.title}'"
    assert card.status.value == status, f"Expected status '{status}', got '{card.status.value}'"


@then(r'the card repository is empty')
def step_card_repo_empty(context):
    cards = list(context.card_repo._store.values())
    assert not cards, f"Expected empty card repository, got {len(cards)}"


@then(r'a BoardCreated event is published')
def step_board_created_event(context):
    events = [e for e in context.published_events if isinstance(e, BoardCreated)]
    assert events, f"Expected BoardCreated event; got: {context.published_events}"


@then(r'a BoardDeleted event is published')
def step_board_deleted_event(context):
    events = [e for e in context.published_events if isinstance(e, BoardDeleted)]
    assert events, f"Expected BoardDeleted event; got: {context.published_events}"


@then(r'a CardCreated event is published')
def step_card_created_event(context):
    events = [e for e in context.published_events if isinstance(e, CardCreated)]
    assert events, f"Expected CardCreated event; got: {context.published_events}"


@then(r'a CardUpdated event is published')
def step_card_updated_event(context):
    events = [e for e in context.published_events if isinstance(e, CardUpdated)]
    assert events, f"Expected CardUpdated event; got: {context.published_events}"


@then(r'a CardDeleted event is published')
def step_card_deleted_event(context):
    events = [e for e in context.published_events if isinstance(e, CardDeleted)]
    assert events, f"Expected CardDeleted event; got: {context.published_events}"


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
