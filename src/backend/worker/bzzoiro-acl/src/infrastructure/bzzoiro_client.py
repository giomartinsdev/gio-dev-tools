from __future__ import annotations

from datetime import date, datetime
from typing import Optional, Union

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from shared.logger import get_logger

logger = get_logger(__name__)

# football is the only free bzzoiro sport and lives at the root of /api/ per
# llms.txt; the WebSocket docs reference /api/v2/... for other sports, so
# confirm this prefix against Swagger (/api/docs/) before relying on it in
# production — see docs/bzzoiro-docs.md section 4.
_BASE_URL = "https://sports.bzzoiro.com/api/"
_MAX_PAGE_SIZE = 200


class BzzoiroAuthError(Exception):
    """401/403 from bzzoiro — a config problem, not transient."""


class BzzoiroRateLimited(Exception):
    def __init__(self, retry_after: float):
        self.retry_after = retry_after
        super().__init__(f"rate limited, retry after {retry_after}s")


class BzzoiroClient:
    def __init__(self, api_key: str, base_url: str = _BASE_URL, timeout: float = 15.0):
        self._headers = {"Authorization": f"Token {api_key}"}
        self._base_url = base_url
        self._timeout = timeout

    @retry(
        retry=retry_if_exception_type(BzzoiroRateLimited),
        wait=wait_exponential(multiplier=1, min=1, max=60),
        stop=stop_after_attempt(6),
        reraise=True,
    )
    def _get(self, client: httpx.Client, path: str, params: dict, not_found_default: Union[dict, list]):
        resp = client.get(path, params=params)
        if resp.status_code == 429:
            retry_after = float(resp.headers.get("Retry-After", "5"))
            raise BzzoiroRateLimited(retry_after)
        if resp.status_code in (401, 403):
            raise BzzoiroAuthError(f"{resp.status_code} from bzzoiro — check BZZOIRO_API_KEY")
        if resp.status_code == 404:
            return not_found_default
        resp.raise_for_status()
        return resp.json()

    def _paginate(self, path: str, params: dict) -> list[dict]:
        """Paginate a v1-style `{count, next, previous, results}` envelope."""
        results: list[dict] = []
        limit = min(int(params.get("limit", _MAX_PAGE_SIZE)), _MAX_PAGE_SIZE)
        offset = 0
        with httpx.Client(base_url=self._base_url, headers=self._headers, timeout=self._timeout) as client:
            while True:
                page = self._get(client, path, {**params, "limit": limit, "offset": offset}, {})
                results.extend(page.get("results") or [])
                if not page.get("next"):
                    break
                offset += limit
        return results

    def _paginate_v2(self, path: str, params: dict) -> list[dict]:
        """Paginate a v2 endpoint. The OpenAPI schema documents a plain JSON
        array, but the real API has been observed returning the same
        `{count, next, previous, results}` envelope v1 uses — accept either
        shape rather than trusting the docs (bitten by this once already
        with `status`)."""
        results: list[dict] = []
        limit = min(int(params.get("limit", _MAX_PAGE_SIZE)), _MAX_PAGE_SIZE)
        offset = 0
        with httpx.Client(base_url=self._base_url, headers=self._headers, timeout=self._timeout) as client:
            while True:
                page = self._get(client, path, {**params, "limit": limit, "offset": offset}, [])
                if isinstance(page, dict):
                    results.extend(page.get("results") or [])
                    if not page.get("next"):
                        break
                    offset += limit
                    continue
                if isinstance(page, list):
                    results.extend(page)
                    if len(page) < limit:
                        break
                    offset += limit
                    continue
                break
        return results

    def fetch_events(
        self,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        status: Optional[str] = None,
    ) -> list[dict]:
        params: dict = {}
        if date_from:
            params["date_from"] = date_from.isoformat()
        if date_to:
            params["date_to"] = date_to.isoformat()
        if status:
            params["status"] = status
        return self._paginate("events/", params)

    def fetch_live(self) -> list[dict]:
        return self._paginate("live/", {})

    def fetch_odds(self, updated_after: Optional[datetime] = None) -> list[dict]:
        """GET /api/v2/odds/ — flat list of OddsItemV2Schema (one row per
        bookmaker+market+outcome, not grouped)."""
        params: dict = {}
        if updated_after:
            params["updated_after"] = updated_after.isoformat()
        return self._paginate_v2("v2/odds/", params)

    def fetch_predictions(self, status: str = "upcoming") -> list[dict]:
        """GET /api/v2/predictions/ — list of PredictionV2Schema."""
        return self._paginate_v2("v2/predictions/", {"status": status})
