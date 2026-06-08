import os
import httpx
from shared.logger import get_logger

logger = get_logger(__name__)

_BASE_URL = os.environ["TRENS_RJ_API_URL"].rstrip("/")


class TrensRjClient:
    def __init__(self):
        self._client = httpx.Client(base_url=_BASE_URL, timeout=30.0)

    def get_stations(self) -> list[dict]:
        response = self._client.get("/stations/")
        response.raise_for_status()
        return response.json()

    def get_lines(self) -> list[dict]:
        response = self._client.get("/lines/")
        response.raise_for_status()
        return response.json()

    def get_live_trip(self, station_id: str, line_id: str, direction: str) -> dict:
        response = self._client.get(
            "/trips/live",
            params={"stationId": station_id, "lineId": line_id, "direction": direction},
        )
        response.raise_for_status()
        return response.json()

    def close(self):
        self._client.close()
