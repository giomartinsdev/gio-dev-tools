from pydantic import BaseModel
from ...domain.repository import StationRepository
from ...domain.station import Station


class ListStationsQuery(BaseModel):
    pass


class ListStationsHandler:
    def __init__(self, repo: StationRepository):
        self._repo = repo

    def handle(self, query: ListStationsQuery) -> list[Station]:
        return self._repo.find_all()
