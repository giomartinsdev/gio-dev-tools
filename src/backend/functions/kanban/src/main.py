import os

from shared.logger import get_logger
from shared.request import Request
from shared.response import Response
from shared.transaction_manager import TransactionConfig, TransactionManager

from .application.commands.create_board import CreateBoardCommand, CreateBoardHandler
from .application.commands.create_card import CreateCardCommand, CreateCardHandler
from .application.commands.delete_board import DeleteBoardCommand, DeleteBoardHandler
from .application.commands.delete_card import DeleteCardCommand, DeleteCardHandler
from .application.commands.update_card import UpdateCardCommand, UpdateCardHandler
from .domain.events import BoardCreated, BoardDeleted, CardCreated, CardDeleted, CardUpdated
from .infrastructure.event_bus import get_event_bus
from .infrastructure.models import Base
from .infrastructure.repository import PostgresBoardRepository, PostgresCardRepository

logger = get_logger(__name__)

TransactionManager.configure(TransactionConfig(url=os.environ["DATABASE_URL"]))
Base.metadata.create_all(TransactionManager.get().engine)

_board_repo = PostgresBoardRepository()
_card_repo = PostgresCardRepository()
_bus = get_event_bus()

_bus.subscribe(BoardCreated, lambda e: logger.info(f"BoardCreated id={e.board_id} name={e.name}"))
_bus.subscribe(BoardDeleted, lambda e: logger.info(f"BoardDeleted id={e.board_id}"))
_bus.subscribe(CardCreated, lambda e: logger.info(f"CardCreated id={e.card_id} board={e.board_id} status={e.status}"))
_bus.subscribe(CardUpdated, lambda e: logger.info(f"CardUpdated id={e.card_id} board={e.board_id} status={e.status}"))
_bus.subscribe(CardDeleted, lambda e: logger.info(f"CardDeleted id={e.card_id}"))


def main(request: Request) -> Response:
    try:
        body = request.body if isinstance(request.body, dict) else {}
        resource = body.get("resource", "card")

        if request.method == "GET":
            board_id = request.query.get("board_id")
            if board_id:
                return _list_cards(board_id)
            return _list_boards()

        if request.method == "POST":
            if resource == "board":
                return _create_board(body)
            return _create_card(body)

        if request.method == "PATCH":
            return _update_card(body)

        if request.method == "DELETE":
            if resource == "board":
                return _delete_board(body)
            return _delete_card(body)

        return Response(body={"error": "method not allowed"}, status_code=405)

    except ValueError as e:
        return Response(body={"error": str(e)}, status_code=400)
    except Exception as e:
        logger.error(f"unhandled error: {e}", exc_info=True)
        return Response(body={"error": "internal server error"}, status_code=500)


def _list_boards() -> Response:
    boards = _board_repo.find_all()
    return Response(body=[b.to_dict() for b in boards], status_code=200)


def _create_board(body: dict) -> Response:
    board = CreateBoardHandler(_board_repo, _bus).handle(
        CreateBoardCommand(name=str(body.get("name", "")))
    )
    return Response(body=board.to_dict(), status_code=201)


def _delete_board(body: dict) -> Response:
    deleted = DeleteBoardHandler(_board_repo, _bus).handle(
        DeleteBoardCommand(board_id=str(body.get("id", "")))
    )
    if not deleted:
        return Response(body={"error": "board not found"}, status_code=404)
    return Response(body={"deleted": True}, status_code=200)


def _list_cards(board_id: str) -> Response:
    cards = _card_repo.find_by_board(board_id)
    return Response(body=[c.to_dict() for c in cards], status_code=200)


def _create_card(body: dict) -> Response:
    card = CreateCardHandler(_card_repo, _bus).handle(
        CreateCardCommand(
            board_id=str(body.get("board_id", "")),
            title=str(body.get("title", "")),
            content=str(body.get("content", "")),
            status=str(body.get("status", "todo")),
        )
    )
    return Response(body=card.to_dict(), status_code=201)


def _update_card(body: dict) -> Response:
    result = UpdateCardHandler(_card_repo, _bus).handle(
        UpdateCardCommand(
            card_id=str(body.get("id", "")),
            title=str(body.get("title", "")),
            content=str(body.get("content", "")),
            status=str(body.get("status", "todo")),
            board_id=str(body.get("board_id", "")),
        )
    )
    if result is None:
        return Response(body={"error": "card not found"}, status_code=404)
    return Response(body=result.to_dict(), status_code=200)


def _delete_card(body: dict) -> Response:
    deleted = DeleteCardHandler(_card_repo, _bus).handle(
        DeleteCardCommand(card_id=str(body.get("id", "")))
    )
    if not deleted:
        return Response(body={"error": "card not found"}, status_code=404)
    return Response(body={"deleted": True}, status_code=200)
