from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from behave import given, then, use_step_matcher, when

from src.infrastructure.osrm_client import OsrmClient

use_step_matcher("re")


def _make_client_cm(response=None, exc=None):
    client = AsyncMock()
    if exc is not None:
        client.get = AsyncMock(side_effect=exc)
    else:
        client.get = AsyncMock(return_value=response)
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=client)
    cm.__aexit__ = AsyncMock(return_value=False)
    return cm


@given(r"OSRM will respond with status (\d+) and duration (\d+) seconds")
def step_osrm_success(context, status, duration):
    response = MagicMock()
    response.status_code = int(status)
    response.json = MagicMock(return_value={"routes": [{"duration": float(duration)}]})
    context.client_cm = _make_client_cm(response=response)


@given(r"OSRM will respond with status (\d+)")
def step_osrm_status(context, status):
    response = MagicMock()
    response.status_code = int(status)
    context.client_cm = _make_client_cm(response=response)


@given("OSRM will raise a connection error")
def step_osrm_error(context):
    context.client_cm = _make_client_cm(exc=RuntimeError("connection refused"))


@when(r'I request a "([^"]+)" route')
def step_request(context, profile):
    client = OsrmClient()

    async def run():
        with patch("httpx.AsyncClient", return_value=context.client_cm):
            return await client.route_minutes(profile, (-43.2, -22.9), (-43.21, -22.91))

    context.result = asyncio.run(run())


@then(r"the route result is ([\d.]+) minutes")
def step_assert_minutes(context, minutes):
    assert context.result == float(minutes), f"expected {minutes}, got {context.result}"


@then("the route result is None")
def step_assert_none(context):
    assert context.result is None
