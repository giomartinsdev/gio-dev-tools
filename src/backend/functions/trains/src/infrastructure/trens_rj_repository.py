from ..domain.repository import LineRepository, StationRepository, TripRepository
from ..domain.station import Line, Station
from ..domain.trip import LiveTrip
from .trens_rj_client import TrensRjClient


class TrensRjStationRepository(StationRepository):
    def __init__(self, client: TrensRjClient):
        self._client = client

    def find_all(self) -> list[Station]:
        return [Station.from_api(s) for s in self._client.get_stations()]


class TrensRjLineRepository(LineRepository):
    def __init__(self, client: TrensRjClient):
        self._client = client

    def find_all(self) -> list[Line]:
        return [Line.from_api(l) for l in self._client.get_lines()]


class TrensRjTripRepository(TripRepository):
    def __init__(self, client: TrensRjClient):
        self._client = client

    def find_live(self, station_id: str, line_id: str, direction: str) -> LiveTrip:
        data = self._client.get_live_trip(station_id, line_id, direction)
        return LiveTrip.from_api(data, station_id=station_id, line_id=line_id, direction=direction)
