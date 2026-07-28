from __future__ import annotations

import os

import httpx

_DEFAULT_BASE_URL = os.environ.get("BUS_TRACKER_URL", "http://bus-tracker:8000")


class BusTrackerClient:
    """Talks to the bus-tracker api over the internal docker network — the
    same cross-service HTTP pattern already used by finance-ocr → finance,
    rather than reaching into tables owned by another service directly."""

    def __init__(self, base_url: str = _DEFAULT_BASE_URL, timeout: float = 10.0):
        self._base_url = base_url
        self._timeout = timeout

    def ensure_tracked_line(self, mode: str, line_code: str) -> None:
        with httpx.Client(timeout=self._timeout) as client:
            resp = client.get(f"{self._base_url}/lines")
            resp.raise_for_status()
            lines = resp.json()
            if any(line["mode"] == mode and line["line_code"] == line_code for line in lines):
                return
            client.post(
                f"{self._base_url}/lines",
                json={"line_code": line_code, "mode": mode, "label": "", "active": True},
            )

    def find_latest_positions(self, mode: str, line_code: str) -> list[dict]:
        with httpx.Client(timeout=self._timeout) as client:
            resp = client.get(f"{self._base_url}/positions/latest", params={"mode": mode, "line": line_code})
            resp.raise_for_status()
            return resp.json()

    def find_stops(self, mode: str, line_code: str) -> list[dict]:
        with httpx.Client(timeout=self._timeout) as client:
            resp = client.get(f"{self._base_url}/lines/stops", params={"mode": mode, "line": line_code})
            resp.raise_for_status()
            return resp.json()
