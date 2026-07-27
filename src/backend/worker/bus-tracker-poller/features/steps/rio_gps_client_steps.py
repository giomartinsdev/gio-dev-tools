from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import Mock, patch

import httpx
from behave import given, then, use_step_matcher, when

from src.infrastructure.rio_gps_client import (
    RioGpsClient,
    RioGpsTransientError,
    parse_brt_position,
    parse_sppo_position,
)

use_step_matcher("re")


def _response(status_code: int, json_body) -> Mock:
    resp = Mock(spec=httpx.Response)
    resp.status_code = status_code
    resp.json.return_value = json_body

    def _raise_for_status():
        if status_code >= 400:
            raise httpx.HTTPStatusError("error", request=Mock(), response=resp)

    resp.raise_for_status.side_effect = _raise_for_status
    return resp


def _setup(context):
    context.client = RioGpsClient()
    context.result = None
    context.error = None


@given('a fresh RioGpsClient')
def step_fresh_client(context):
    _setup(context)


@given('the SPPO feed returns 200 with 2 rows')
def step_feed_ok(context):
    _setup(context)
    rows = [{"ordem": "A1", "linha": "483"}, {"ordem": "B1", "linha": "606"}]
    resp = _response(200, rows)
    context.get_patch = patch.object(httpx.Client, "get", side_effect=[resp])


@given('the SPPO feed returns 502 once then succeeds')
def step_feed_502_then_ok(context):
    _setup(context)
    resp_502 = _response(502, {})
    resp_ok = _response(200, [{"ordem": "A1", "linha": "483"}])
    context.get_patch = patch.object(httpx.Client, "get", side_effect=[resp_502, resp_ok])
    context.sleep_patch = patch("tenacity.nap.sleep")


@given('the SPPO feed always times out')
def step_feed_timeout(context):
    _setup(context)
    context.get_patch = patch.object(
        httpx.Client, "get", side_effect=httpx.ReadTimeout("timed out", request=Mock())
    )
    context.sleep_patch = patch("tenacity.nap.sleep")


@when('I fetch positions from the client')
def step_fetch_positions(context):
    sleep_patch = getattr(context, "sleep_patch", None)
    now = datetime.now(timezone.utc)
    with context.get_patch:
        if sleep_patch is not None:
            with sleep_patch:
                _do_fetch(context, now)
        else:
            _do_fetch(context, now)


def _do_fetch(context, now):
    try:
        context.result = context.client.fetch_sppo_positions(now, now)
    except Exception as e:
        context.error = e


@then('all rows are returned')
def step_all_rows(context):
    assert context.error is None, f"unexpected error: {context.error}"
    assert [r["ordem"] for r in context.result] == ["A1", "B1"], context.result


@then('the row after retry is returned')
def step_row_after_retry(context):
    assert context.error is None, f"unexpected error: {context.error}"
    assert [r["ordem"] for r in context.result] == ["A1"]


@then('a RioGpsTransientError is raised')
def step_transient_error(context):
    assert isinstance(context.error, RioGpsTransientError), (
        f"expected RioGpsTransientError, got {context.error!r}"
    )


@given('a well-formed SPPO row')
def step_wellformed_row(context):
    context.row = {
        "ordem": "B25611", "latitude": "-22,90434", "longitude": "-43,2863",
        "datahora": "1785121192000", "velocidade": "0", "linha": "606",
    }


@given('a SPPO row missing the latitude field')
def step_missing_field_row(context):
    context.row = {"ordem": "B25611", "linha": "606"}


@when('I parse the row')
def step_parse_row(context):
    try:
        context.parsed = parse_sppo_position(context.row)
        context.error = None
    except ValueError as e:
        context.error = e
        context.parsed = None


@then(r'the parsed position has line_code "([^"]+)" and vehicle_id "([^"]+)"')
def step_assert_parsed(context, line_code, vehicle_id):
    assert context.error is None, context.error
    assert context.parsed["line_code"] == line_code
    assert context.parsed["vehicle_id"] == vehicle_id
    assert context.parsed["latitude"] == -22.90434
    assert context.parsed["longitude"] == -43.2863
    assert context.parsed["mode"] == "sppo"


@then('a ValueError is raised for the malformed row')
def step_assert_value_error(context):
    assert isinstance(context.error, ValueError), context.error


# ── BRT ────────────────────────────────────────────────────────────────────

@given('the BRT feed returns 200 with 2 vehicles')
def step_brt_feed_ok(context):
    _setup(context)
    envelope = {"veiculos": [
        {"codigo": "901008", "linha": "22", "latitude": -23.001127, "longitude": -43.329477,
         "dataHora": 1785181063000, "velocidade": 11},
        {"codigo": "901011", "linha": "50", "latitude": -22.973315, "longitude": -43.392935,
         "dataHora": 1785181071000, "velocidade": 0},
    ]}
    resp = _response(200, envelope)
    context.get_patch = patch.object(httpx.Client, "get", side_effect=[resp])


@when('I fetch BRT positions from the client')
def step_fetch_brt(context):
    with context.get_patch:
        try:
            context.result = context.client.fetch_brt_positions()
        except Exception as e:
            context.error = e


@then('both BRT vehicles are returned')
def step_both_brt_vehicles(context):
    assert context.error is None, f"unexpected error: {context.error}"
    assert [r["codigo"] for r in context.result] == ["901008", "901011"], context.result


@given('a well-formed BRT row')
def step_wellformed_brt_row(context):
    context.row = {
        "codigo": "901008", "linha": "22", "latitude": -23.001127,
        "longitude": -43.329477, "dataHora": 1785181063000, "velocidade": 11,
    }


@given('a BRT row missing the codigo field')
def step_missing_codigo_row(context):
    context.row = {"linha": "22", "latitude": -23.001127, "longitude": -43.329477}


@when('I parse the BRT row')
def step_parse_brt_row(context):
    try:
        context.parsed = parse_brt_position(context.row)
        context.error = None
    except ValueError as e:
        context.error = e
        context.parsed = None


@then(r'the parsed BRT position has line_code "([^"]+)" and vehicle_id "([^"]+)"')
def step_assert_parsed_brt(context, line_code, vehicle_id):
    assert context.error is None, context.error
    assert context.parsed["line_code"] == line_code
    assert context.parsed["vehicle_id"] == vehicle_id
    assert context.parsed["mode"] == "brt"


@then('a ValueError is raised for the malformed BRT row')
def step_assert_brt_value_error(context):
    assert isinstance(context.error, ValueError), context.error


# ── vehicle colors ──────────────────────────────────────────────────────────

@given('the vehicle colors endpoint returns 2 entries')
def step_colors_ok(context):
    _setup(context)
    rows = [
        {"ordem": "D33082", "cor_hex": "#9E652E"},
        {"ordem": "D33083", "cor_hex": "#112233"},
    ]
    resp = _response(200, rows)
    context.get_patch = patch.object(httpx.Client, "get", side_effect=[resp])


@given('the vehicle colors endpoint is unreachable')
def step_colors_unreachable(context):
    _setup(context)
    context.get_patch = patch.object(
        httpx.Client, "get", side_effect=httpx.ConnectError("refused", request=Mock())
    )


@when('I fetch vehicle colors from the client')
def step_fetch_colors(context):
    with context.get_patch:
        context.result = context.client.fetch_vehicle_colors()


@then(r'the color map has (\d+) entries')
def step_assert_color_count(context, count):
    assert len(context.result) == int(count), context.result


@then('the color map is empty')
def step_assert_color_map_empty(context):
    assert context.result == {}, context.result
