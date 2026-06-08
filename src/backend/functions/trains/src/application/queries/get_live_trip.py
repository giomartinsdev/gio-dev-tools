from pydantic import BaseModel
from ...domain.repository import TripRepository
from ...domain.trip import LiveTrip


class GetLiveTripQuery(BaseModel):
    station_id: str
    line_id: str
    direction: str
    date: str | None = None
    time: str | None = None


class GetLiveTripHandler:
    def __init__(self, repo: TripRepository):
        self._repo = repo

    def handle(self, query: GetLiveTripQuery) -> LiveTrip:
        return self._repo.find_live(
            station_id=query.station_id,
            line_id=query.line_id,
            direction=query.direction,
            date=query.date,
            time=query.time,
        )
