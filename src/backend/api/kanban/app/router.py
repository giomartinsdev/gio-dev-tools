from fastapi import APIRouter, Depends, HTTPException

from src.application.commands.create_board import CreateBoardCommand, CreateBoardHandler
from src.application.commands.delete_board import DeleteBoardCommand, DeleteBoardHandler
from src.application.commands.create_card import CreateCardCommand, CreateCardHandler
from src.application.commands.update_card import UpdateCardCommand, UpdateCardHandler
from src.application.commands.delete_card import DeleteCardCommand, DeleteCardHandler
from src.infrastructure.repository import PostgresBoardRepository, PostgresCardRepository
from src.infrastructure.event_bus import EventBus

from .schemas import (
    BoardResponse,
    CardResponse,
    CreateBoardRequest,
    CreateCardRequest,
    UpdateCardRequest,
)
from .deps import get_board_repo, get_card_repo, get_bus

router = APIRouter()


@router.get("/boards", response_model=list[BoardResponse])
def list_boards(board_repo: PostgresBoardRepository = Depends(get_board_repo)):
    return [BoardResponse(id=b.id, name=b.name) for b in board_repo.find_all()]


@router.post("/boards", response_model=BoardResponse, status_code=201)
def create_board(
    body: CreateBoardRequest,
    board_repo: PostgresBoardRepository = Depends(get_board_repo),
    bus: EventBus = Depends(get_bus),
):
    try:
        board = CreateBoardHandler(board_repo, bus).handle(CreateBoardCommand(name=body.name))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return BoardResponse(id=board.id, name=board.name)


@router.delete("/boards/{board_id}", status_code=200)
def delete_board(
    board_id: str,
    board_repo: PostgresBoardRepository = Depends(get_board_repo),
    bus: EventBus = Depends(get_bus),
):
    deleted = DeleteBoardHandler(board_repo, bus).handle(DeleteBoardCommand(board_id=board_id))
    if not deleted:
        raise HTTPException(status_code=404, detail="board not found")
    return {"deleted": True}


@router.get("/boards/{board_id}/cards", response_model=list[CardResponse])
def list_cards(
    board_id: str,
    card_repo: PostgresCardRepository = Depends(get_card_repo),
):
    cards = card_repo.find_by_board(board_id)
    return [
        CardResponse(
            id=c.id,
            board_id=c.board_id,
            title=c.title,
            content=c.content,
            status=c.status.value,
        )
        for c in cards
    ]


@router.post("/boards/{board_id}/cards", response_model=CardResponse, status_code=201)
def create_card(
    board_id: str,
    body: CreateCardRequest,
    card_repo: PostgresCardRepository = Depends(get_card_repo),
    bus: EventBus = Depends(get_bus),
):
    try:
        card = CreateCardHandler(card_repo, bus).handle(
            CreateCardCommand(
                board_id=board_id,
                title=body.title,
                content=body.content,
                status=body.status,
            )
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return CardResponse(
        id=card.id,
        board_id=card.board_id,
        title=card.title,
        content=card.content,
        status=card.status.value,
    )


@router.patch("/cards/{card_id}", response_model=CardResponse)
def update_card(
    card_id: str,
    body: UpdateCardRequest,
    card_repo: PostgresCardRepository = Depends(get_card_repo),
    bus: EventBus = Depends(get_bus),
):
    try:
        card = UpdateCardHandler(card_repo, bus).handle(
            UpdateCardCommand(
                card_id=card_id,
                title=body.title,
                content=body.content,
                status=body.status,
                board_id=body.board_id,
            )
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if card is None:
        raise HTTPException(status_code=404, detail="card not found")
    return CardResponse(
        id=card.id,
        board_id=card.board_id,
        title=card.title,
        content=card.content,
        status=card.status.value,
    )


@router.delete("/cards/{card_id}", status_code=200)
def delete_card(
    card_id: str,
    card_repo: PostgresCardRepository = Depends(get_card_repo),
    bus: EventBus = Depends(get_bus),
):
    deleted = DeleteCardHandler(card_repo, bus).handle(DeleteCardCommand(card_id=card_id))
    if not deleted:
        raise HTTPException(status_code=404, detail="card not found")
    return {"deleted": True}
