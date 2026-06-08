from abc import ABC, abstractmethod
from .station import Line, Station
from .trip import LiveTrip


class StationRepository(ABC):
    @abstractmethod
    def find_all(self) -> list[Station]: ...


class LineRepository(ABC):
    @abstractmethod
    def find_all(self) -> list[Line]: ...


class TripRepository(ABC):
    @abstractmethod
    def find_live(self, station_id: str, line_id: str, direction: str) -> LiveTrip: ...
