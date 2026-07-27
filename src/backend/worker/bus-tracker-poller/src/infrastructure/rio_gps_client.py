from __future__ import annotations

from datetime import datetime, timezone

import httpcore
import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from shared.logger import get_logger

logger = get_logger(__name__)

# Public, unauthenticated feed — confirmed live: it returns every bus in the
# city for the requested window, there is no server-side `linha` filter, so
# callers must filter the returned rows by line code themselves.
_BASE_URL = "https://dados.mobilidade.rio/gps/sppo"


class RioGpsTransientError(Exception):
    """Timeout/5xx from the feed — transient, safe to retry."""


class RioGpsClient:
    def __init__(self, base_url: str = _BASE_URL, timeout: float = 60.0):
        self._base_url = base_url
        self._timeout = timeout

    @retry(
        retry=retry_if_exception_type(RioGpsTransientError),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        stop=stop_after_attempt(4),
        reraise=True,
    )
    def _get(self, client: httpx.Client, params: dict) -> list[dict]:
        try:
            resp = client.get(self._base_url, params=params)
        except (httpx.ReadTimeout, httpcore.ReadTimeout) as exc:
            raise RioGpsTransientError(f"ReadTimeout on {self._base_url}") from exc
        if resp.status_code in (502, 503, 504):
            raise RioGpsTransientError(f"{resp.status_code} from {self._base_url}")
        resp.raise_for_status()
        return resp.json()

    def fetch_positions(self, data_inicial: datetime, data_final: datetime) -> list[dict]:
        """GET dados.mobilidade.rio/gps/sppo — every SPPO bus GPS ping in the
        requested window, city-wide. Each row looks like:
        `{"ordem": "B25611", "latitude": "-22,90434", "longitude": "-43,2863",
          "datahora": "1785121192000", "velocidade": "0", "linha": "606",
          "datahoraenvio": "...", "datahoraservidor": "..."}` — lat/lon use a
        comma decimal separator and `datahora` is epoch milliseconds, both
        confirmed against a live sample."""
        params = {
            "dataInicial": data_inicial.strftime("%Y-%m-%d %H:%M:%S"),
            "dataFinal": data_final.strftime("%Y-%m-%d %H:%M:%S"),
        }
        with httpx.Client(timeout=self._timeout) as client:
            return self._get(client, params)


def parse_position(row: dict) -> dict:
    """Translate one raw SPPO row into typed fields ready for a
    BusPositionCaptured event. Raises ValueError on a malformed row (missing
    `linha`/`ordem`, or lat/lon/datahora that can't be parsed) so the caller
    can skip it rather than publish garbage."""
    try:
        latitude = float(str(row["latitude"]).replace(",", "."))
        longitude = float(str(row["longitude"]).replace(",", "."))
        speed_kmh = float(str(row.get("velocidade", "0")).replace(",", "."))
        captured_at = datetime.fromtimestamp(int(row["datahora"]) / 1000, tz=timezone.utc)
        line_code = str(row["linha"])
        vehicle_id = str(row["ordem"])
    except (KeyError, ValueError, TypeError) as exc:
        raise ValueError(f"malformed SPPO row: {row!r}") from exc
    return {
        "line_code": line_code,
        "vehicle_id": vehicle_id,
        "latitude": latitude,
        "longitude": longitude,
        "speed_kmh": speed_kmh,
        "captured_at": captured_at,
    }
