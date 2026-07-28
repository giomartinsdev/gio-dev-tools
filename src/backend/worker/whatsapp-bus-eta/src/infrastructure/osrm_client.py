from __future__ import annotations

from typing import Optional

import httpx

# Same free, no-API-key OSRM demo server the dashboard's map calls directly
# from the browser — used here server-side since a WhatsApp reply has no
# browser to make the CORS-friendly call from.
_OSRM_URL = "https://router.project-osrm.org"


class OsrmClient:
    def __init__(self, base_url: str = _OSRM_URL, timeout: float = 10.0):
        self._base_url = base_url
        self._timeout = timeout

    async def route_minutes(
        self, profile: str, from_lonlat: tuple[float, float], to_lonlat: tuple[float, float],
    ) -> Optional[float]:
        coords = f"{from_lonlat[0]},{from_lonlat[1]};{to_lonlat[0]},{to_lonlat[1]}"
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.get(f"{self._base_url}/route/v1/{profile}/{coords}", params={"overview": "false"})
                if resp.status_code != 200:
                    return None
                data = resp.json()
                duration = data.get("routes", [{}])[0].get("duration")
                return duration / 60 if isinstance(duration, (int, float)) else None
        except Exception:
            return None
