from __future__ import annotations

from typing import Optional

from pydantic import BaseModel

from ...infrastructure.read_model_repository import ReadModelRepository


class ListInsightsQuery(BaseModel):
    match_id: Optional[str] = None
    limit: int = 50
    offset: int = 0


class ListInsightsHandler:
    def __init__(self, repo: ReadModelRepository):
        self._repo = repo

    def handle(self, query: ListInsightsQuery) -> list[dict]:
        return self._repo.find_insights(match_id=query.match_id, limit=query.limit, offset=query.offset)
