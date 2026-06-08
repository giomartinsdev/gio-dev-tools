from dataclasses import dataclass, field


@dataclass
class LiveTrip:
    station_id: str
    line_id: str
    direction: str
    raw: dict = field(repr=False, default_factory=dict)

    @classmethod
    def from_api(cls, data: dict, station_id: str, line_id: str, direction: str) -> "LiveTrip":
        return cls(
            station_id=station_id,
            line_id=line_id,
            direction=direction,
            raw=data,
        )

    def to_dict(self) -> dict:
        return {**self.raw, "stationId": self.station_id, "lineId": self.line_id, "direction": self.direction}
