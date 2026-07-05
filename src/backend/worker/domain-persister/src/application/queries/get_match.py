from __future__ import annotations

from typing import Optional

from pydantic import BaseModel

from ...infrastructure.read_model_repository import ReadModelRepository


class GetMatchQuery(BaseModel):
    match_id: str


class GetMatchHandler:
    def __init__(self, repo: ReadModelRepository):
        self._repo = repo

    def handle(self, query: GetMatchQuery) -> Optional[dict]:
        return self._repo.find_match(query.match_id)
