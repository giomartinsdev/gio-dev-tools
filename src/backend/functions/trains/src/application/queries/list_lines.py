from pydantic import BaseModel
from ...domain.repository import LineRepository
from ...domain.station import Line


class ListLinesQuery(BaseModel):
    pass


class ListLinesHandler:
    def __init__(self, repo: LineRepository):
        self._repo = repo

    def handle(self, query: ListLinesQuery) -> list[Line]:
        return self._repo.find_all()
