from __future__ import annotations

from typing import Optional

from pydantic import BaseModel

from ...infrastructure.read_model_repository import ReadModelRepository


class ListValueBetOutcomesQuery(BaseModel):
    match_id: Optional[str] = None
    limit: int = 50
    offset: int = 0


class ListValueBetOutcomesHandler:
    def __init__(self, repo: ReadModelRepository):
        self._repo = repo

    def handle(self, query: ListValueBetOutcomesQuery) -> list[dict]:
        return self._repo.find_value_bet_outcomes(match_id=query.match_id, limit=query.limit, offset=query.offset)


class SummarizeValueBetOutcomesHandler:
    def __init__(self, repo: ReadModelRepository):
        self._repo = repo

    def handle(self) -> dict:
        return self._repo.summarize_value_bet_outcomes()
