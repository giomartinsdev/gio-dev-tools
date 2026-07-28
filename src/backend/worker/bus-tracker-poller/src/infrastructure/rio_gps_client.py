from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import httpcore
import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from shared.logger import get_logger

logger = get_logger(__name__)

# Confirmed live (2026-07-28): the SPPO endpoint interprets dataInicial/
# dataFinal as America/Sao_Paulo wall-clock time, not UTC — the reference
# app (RJ-SMTR/app-monitoramento-realtime) gets this "for free" since it
# formats with the browser's local `Date`, which just happens to be BRT for
# its users. A UTC-formatted window silently returns 200 with an empty
# array (looks exactly like "no live data" — it's actually "no data 3
# hours in the future"), which is why this needed a live sample to catch.
_SP_TZ = ZoneInfo("America/Sao_Paulo")

# Two independent, unauthenticated, public real-time systems — confirmed live
# to behave differently: SPPO (regular buses) needs an explicit time window
# and has no server-side `linha` filter (every bus in the city comes back —
# callers filter by line themselves); BRT is a plain live snapshot, no query
# params at all, already-live vehicles only. Both confirmed against
# RJ-SMTR/app-monitoramento-realtime, the official frontend for this same
# data — its `src/hooks/getGPS.jsx` is the reference this client mirrors.
_SPPO_URL = "https://dados.mobilidade.rio/gps/sppo"
_BRT_URL = "https://dados.mobilidade.rio/gps/brt"
_COLORS_URL = "https://dados.mobilidade.rio/api/monitoramento-realtime/"


class RioGpsTransientError(Exception):
    """Timeout/5xx from a feed — transient, safe to retry."""


class RioGpsClient:
    def __init__(self, timeout: float = 60.0):
        self._timeout = timeout

    @retry(
        retry=retry_if_exception_type(RioGpsTransientError),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        stop=stop_after_attempt(4),
        reraise=True,
    )
    def _get(self, client: httpx.Client, url: str, params: dict | None) -> object:
        try:
            resp = client.get(url, params=params)
        except (httpx.ReadTimeout, httpcore.ReadTimeout) as exc:
            raise RioGpsTransientError(f"ReadTimeout on {url}") from exc
        if resp.status_code in (502, 503, 504):
            raise RioGpsTransientError(f"{resp.status_code} from {url}")
        resp.raise_for_status()
        return resp.json()

    def fetch_sppo_positions(self, data_inicial: datetime, data_final: datetime) -> list[dict]:
        """GET dados.mobilidade.rio/gps/sppo — every regular-bus GPS ping in
        the requested window, city-wide. Each row looks like:
        `{"ordem": "B25611", "latitude": "-22,90434", "longitude": "-43,2863",
          "datahora": "1785121192000", "velocidade": "0", "linha": "606",
          "datahoraenvio": "...", "datahoraservidor": "..."}` — lat/lon use a
        comma decimal separator and `datahora` is epoch milliseconds, both
        confirmed against a live sample.

        Query string is built by hand (`?&dataInicial=...+HH:MM:SS`, `+` as
        the date/time separator) to match RJ-SMTR/app-monitoramento-realtime
        (`format(d, "yyyy-MM-dd+HH:mm:ss")`) byte-for-byte, rather than
        letting httpx's `params=` encode a space — both are accepted by the
        API (confirmed live), but this removes any doubt. `data_inicial`/
        `data_final` may be passed in any timezone (naive datetimes are
        assumed UTC); this always converts to America/Sao_Paulo before
        formatting, since that's what the API actually expects."""
        def _fmt(d: datetime) -> str:
            if d.tzinfo is None:
                d = d.replace(tzinfo=timezone.utc)
            return d.astimezone(_SP_TZ).strftime("%Y-%m-%d+%H:%M:%S")

        url = f"{_SPPO_URL}?&dataInicial={_fmt(data_inicial)}&dataFinal={_fmt(data_final)}"
        with httpx.Client(timeout=self._timeout) as client:
            return self._get(client, url, None)

    def fetch_brt_positions(self) -> list[dict]:
        """GET dados.mobilidade.rio/gps/brt — live BRT snapshot, no query
        params (confirmed: unlike SPPO there's no dataInicial/dataFinal —
        it's always "right now"). Envelope is `{"veiculos": [...]}`, not a
        flat array like SPPO. Each row looks like:
        `{"codigo": "901008", "placa": "RJN9A01", "linha": "22",
          "latitude": -23.001127, "longitude": -43.329477,
          "dataHora": 1785181063000, "velocidade": 11, ...}` — note lat/lon
        and velocidade are already numeric here (no comma decimal), and the
        vehicle identifier field is `codigo`, not `ordem`."""
        with httpx.Client(timeout=self._timeout) as client:
            envelope = self._get(client, _BRT_URL, {})
        if isinstance(envelope, dict):
            return envelope.get("veiculos") or []
        return []

    def fetch_vehicle_colors(self) -> dict[str, str]:
        """GET dados.mobilidade.rio/api/monitoramento-realtime/ — per-vehicle
        operator metadata keyed by SPPO `ordem`, including `cor_hex` (the
        operator's livery color, used to color map markers). Confirmed live:
        BRT vehicles (keyed by `codigo` elsewhere) don't appear here, so BRT
        positions simply get no color match — callers should treat a miss as
        "no color available", not an error. Best-effort: any failure here
        must never block position polling, so this swallows transient errors
        and returns an empty map rather than retrying/raising."""
        try:
            with httpx.Client(timeout=self._timeout) as client:
                rows = self._get(client, _COLORS_URL, {})
        except Exception as exc:
            logger.warning(f"failed to fetch vehicle colors, continuing without them: {exc}")
            return {}
        if not isinstance(rows, list):
            return {}
        return {
            str(row["ordem"]): row["cor_hex"]
            for row in rows
            if isinstance(row, dict) and row.get("ordem") and row.get("cor_hex")
        }


def parse_sppo_position(row: dict) -> dict:
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
        "mode": "sppo",
        "line_code": line_code,
        "vehicle_id": vehicle_id,
        "latitude": latitude,
        "longitude": longitude,
        "speed_kmh": speed_kmh,
        "captured_at": captured_at,
    }


def parse_brt_position(row: dict) -> dict:
    """Translate one raw BRT row into the same typed shape parse_sppo_position
    produces. BRT's lat/lon/velocidade are already numeric (no comma decimal
    to strip) and its vehicle identifier field is `codigo`, not `ordem`."""
    try:
        latitude = float(row["latitude"])
        longitude = float(row["longitude"])
        speed_kmh = float(row.get("velocidade", 0))
        captured_at = datetime.fromtimestamp(int(row["dataHora"]) / 1000, tz=timezone.utc)
        line_code = str(row["linha"])
        vehicle_id = str(row["codigo"])
    except (KeyError, ValueError, TypeError) as exc:
        raise ValueError(f"malformed BRT row: {row!r}") from exc
    return {
        "mode": "brt",
        "line_code": line_code,
        "vehicle_id": vehicle_id,
        "latitude": latitude,
        "longitude": longitude,
        "speed_kmh": speed_kmh,
        "captured_at": captured_at,
    }
