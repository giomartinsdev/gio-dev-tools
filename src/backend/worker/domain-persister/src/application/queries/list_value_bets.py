from __future__ import annotations

from typing import Optional

from pydantic import BaseModel

from ...infrastructure.read_model_repository import ReadModelRepository


class ListValueBetsQuery(BaseModel):
    match_id: Optional[str] = None
    limit: int = 50
    offset: int = 0


class ListValueBetsHandler:
    def __init__(self, repo: ReadModelRepository):
        self._repo = repo

    def handle(self, query: ListValueBetsQuery) -> list[dict]:
        return self._repo.find_value_bets(match_id=query.match_id, limit=query.limit, offset=query.offset)
