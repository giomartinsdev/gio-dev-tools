from typing import Optional

from shared.timezone_handler import TimezoneAware
from shared.transaction_manager import TransactionManager

from ..domain.board import Board
from ..domain.card import Card, CardStatus
from ..domain.repository import BoardRepository, CardRepository
from .models import BoardModel, CardModel

_SP = TimezoneAware("America/Sao_Paulo")


class PostgresBoardRepository(BoardRepository):
    def save(self, board: Board) -> None:
        with TransactionManager.get().session() as s:
            s.add(BoardModel(id=board.id, name=board.name))

    def find_all(self) -> list[Board]:
        with TransactionManager.get().read_only() as s:
            rows = (
                s.query(BoardModel)
                .filter(BoardModel.deleted_at.is_(None))
                .order_by(BoardModel.created_at.asc())
                .all()
            )
            return [_board_from_row(r) for r in rows]

    def find_by_id(self, board_id: str) -> Optional[Board]:
        with TransactionManager.get().read_only() as s:
            row = (
                s.query(BoardModel)
                .filter(BoardModel.id == board_id, BoardModel.deleted_at.is_(None))
                .first()
            )
            return _board_from_row(row) if row else None

    def delete(self, board_id: str) -> bool:
        with TransactionManager.get().session() as s:
            row = s.query(BoardModel).filter(BoardModel.id == board_id, BoardModel.deleted_at.is_(None)).first()
            if not row:
                return False
            row.deleted_at = _SP.now
            return True


class PostgresCardRepository(CardRepository):
    def save(self, card: Card) -> None:
        with TransactionManager.get().session() as s:
            existing = s.query(CardModel).filter(CardModel.id == card.id).first()
            if existing:
                existing.title = card.title
                existing.content = card.content
                existing.status = card.status.value
                existing.board_id = card.board_id
                existing.position = card.position
            else:
                s.add(CardModel(
                    id=card.id,
                    board_id=card.board_id,
                    title=card.title,
                    content=card.content,
                    status=card.status.value,
                    position=card.position,
                ))

    def find_by_board(self, board_id: str) -> list[Card]:
        with TransactionManager.get().read_only() as s:
            rows = (
                s.query(CardModel)
                .filter(CardModel.board_id == board_id, CardModel.deleted_at.is_(None))
                .order_by(CardModel.position.asc(), CardModel.created_at.asc())
                .all()
            )
            return [_card_from_row(r) for r in rows]

    def find_by_id(self, card_id: str) -> Optional[Card]:
        with TransactionManager.get().read_only() as s:
            row = (
                s.query(CardModel)
                .filter(CardModel.id == card_id, CardModel.deleted_at.is_(None))
                .first()
            )
            return _card_from_row(row) if row else None

    def delete(self, card_id: str) -> bool:
        with TransactionManager.get().session() as s:
            row = s.query(CardModel).filter(CardModel.id == card_id, CardModel.deleted_at.is_(None)).first()
            if not row:
                return False
            row.deleted_at = _SP.now
            return True


def _board_from_row(row: BoardModel) -> Board:
    return Board(
        id=row.id,
        name=row.name,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _card_from_row(row: CardModel) -> Card:
    return Card(
        id=row.id,
        board_id=row.board_id,
        title=row.title,
        content=row.content,
        status=CardStatus(row.status),
        position=row.position,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )
