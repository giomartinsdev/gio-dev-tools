from __future__ import annotations

import os
from datetime import date

import httpx

from src.domain.report import resolved_date

DOMAIN_DATA_INSIGHTS_URL = os.environ.get("DOMAIN_DATA_INSIGHTS_URL", "http://domain-data-insights:8000")

PAGE_SIZE = 50


class ValueBetsClient:
    """Reads current value bets from the read-only domain-data-insights API
    — never touches bzzoiro_data directly, same boundary every other
    consumer of this data respects."""

    def __init__(self, base_url: str = DOMAIN_DATA_INSIGHTS_URL):
        self._base_url = base_url

    async def fetch(self) -> list[dict]:
        results: list[dict] = []
        offset = 0
        async with httpx.AsyncClient() as client:
            while True:
                resp = await client.get(
                    f"{self._base_url}/value-bets",
                    params={"limit": PAGE_SIZE, "offset": offset},
                    timeout=30.0,
                )
                resp.raise_for_status()
                page = resp.json()
                results.extend(page)
                if len(page) < PAGE_SIZE:
                    break
                offset += PAGE_SIZE
        return results

    async def fetch_outcomes(self, cutoff_date: date) -> list[dict]:
        """Paginates /value-bets/outcomes (most recently resolved first)
        only back to `cutoff_date` — stops as soon as a page's oldest row
        is older than that, instead of scanning the entire history."""
        results: list[dict] = []
        offset = 0
        async with httpx.AsyncClient() as client:
            while True:
                resp = await client.get(
                    f"{self._base_url}/value-bets/outcomes",
                    params={"limit": PAGE_SIZE, "offset": offset},
                    timeout=30.0,
                )
                resp.raise_for_status()
                page = resp.json()
                if not page:
                    break
                results.extend(page)
                oldest_in_page = resolved_date(page[-1])
                if oldest_in_page is not None and oldest_in_page < cutoff_date:
                    break
                if len(page) < PAGE_SIZE:
                    break
                offset += PAGE_SIZE
        return results
