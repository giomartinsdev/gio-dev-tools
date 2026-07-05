from __future__ import annotations

from pydantic import BaseModel

from ...infrastructure.read_model_repository import ReadModelRepository


class ListMatchesQuery(BaseModel):
    limit: int = 50
    offset: int = 0


class ListMatchesHandler:
    def __init__(self, repo: ReadModelRepository):
        self._repo = repo

    def handle(self, query: ListMatchesQuery) -> list[dict]:
        return self._repo.find_all_matches(limit=query.limit, offset=query.offset)
