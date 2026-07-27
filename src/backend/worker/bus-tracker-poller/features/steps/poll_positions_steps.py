import asyncio
from datetime import datetime, timezone

from behave import given, then, use_step_matcher, when

from src.application.commands.poll_positions import PollPositionsCommand, PollPositionsHandler

use_step_matcher("re")


class FakeRioGpsClient:
    def __init__(self, sppo_rows=None, brt_rows=None, colors=None):
        self._sppo_rows = sppo_rows or []
        self._brt_rows = brt_rows or []
        self._colors = colors or {}

    def fetch_sppo_positions(self, data_inicial, data_final) -> list[dict]:
        return self._sppo_rows

    def fetch_brt_positions(self) -> list[dict]:
        return self._brt_rows

    def fetch_vehicle_colors(self) -> dict:
        return self._colors


class FakePublisher:
    def __init__(self):
        self.published = []

    async def publish_domain_event(self, event) -> None:
        self.published.append(event)


class FakeTrackedLinesReadRepository:
    """Mirrors TrackedLinesReadRepository's public surface without touching
    Postgres — same in-memory-fake-in-steps-file pattern used across every
    other service's BDD suite (see settings' InMemoryServiceRepository)."""

    def __init__(self):
        self._active_codes: dict[str, set[str]] = {"sppo": set(), "brt": set()}

    def add(self, line_code: str, mode: str, active: bool) -> None:
        if active:
            self._active_codes[mode].add(line_code)
        else:
            self._active_codes[mode].discard(line_code)

    def find_active_line_codes(self, mode: str) -> set[str]:
        return set(self._active_codes.get(mode, set()))


def _setup(context):
    context.sppo_rows = []
    context.brt_rows = []
    context.colors = {}
    context.publisher = FakePublisher()
    context.tracked_lines = FakeTrackedLinesReadRepository()


@given("no tracked lines exist")
def step_no_lines(context):
    _setup(context)


@given(r'tracked line "([^"]+)" mode "([^"]+)" is active')
def step_line_active(context, line_code, mode):
    if not hasattr(context, "publisher"):
        _setup(context)
    context.tracked_lines.add(line_code, mode, active=True)


@given(r'tracked line "([^"]+)" mode "([^"]+)" is inactive')
def step_line_inactive(context, line_code, mode):
    if not hasattr(context, "publisher"):
        _setup(context)
    context.tracked_lines.add(line_code, mode, active=False)


def _sppo_row(line_code: str, ordem: str) -> dict:
    return {
        "ordem": ordem,
        "latitude": "-22,90434",
        "longitude": "-43,2863",
        "datahora": str(int(datetime.now(timezone.utc).timestamp() * 1000)),
        "velocidade": "30",
        "linha": line_code,
    }


def _brt_row(line_code: str, codigo: str) -> dict:
    return {
        "codigo": codigo,
        "latitude": -22.90434,
        "longitude": -43.2863,
        "dataHora": int(datetime.now(timezone.utc).timestamp() * 1000),
        "velocidade": 25,
        "linha": line_code,
    }


@given(r'the SPPO feed returns positions for lines "([^"]+)", "([^"]+)" and "([^"]+)"')
def step_feed_three_lines(context, line_a, line_b, line_c):
    context.sppo_rows = [
        _sppo_row(line_a, "A1"),
        _sppo_row(line_b, "B1"),
        _sppo_row(line_c, "C1"),
    ]


@given(r'the SPPO feed returns positions for lines "([^"]+)"')
def step_feed_one_line(context, line_code):
    context.sppo_rows = [_sppo_row(line_code, "A1")]


@given(r'the SPPO feed returns a malformed row for line "([^"]+)"')
def step_feed_malformed(context, line_code):
    context.sppo_rows = [{"linha": line_code, "ordem": "A1"}]  # missing latitude/longitude/datahora


@given(r'the BRT feed returns positions for lines "([^"]+)" and "([^"]+)"')
def step_brt_feed_two_lines(context, line_a, line_b):
    context.brt_rows = [_brt_row(line_a, "901001"), _brt_row(line_b, "901002")]


@given(r'the vehicle color feed maps vehicle "([^"]+)" to color "([^"]+)"')
def step_color_feed(context, vehicle_id, color_hex):
    context.colors[vehicle_id] = color_hex


@when("positions are polled")
def step_poll(context):
    client = FakeRioGpsClient(context.sppo_rows, context.brt_rows, context.colors)
    handler = PollPositionsHandler(client, context.tracked_lines, context.publisher)
    context.published_count = asyncio.run(handler.handle(PollPositionsCommand()))


@then(r"(\d+) positions? (?:is|are) published")
def step_count_published(context, count):
    assert context.published_count == int(count), \
        f"Expected {count} published, got {context.published_count}"


@then(r'a position for line "([^"]+)" is published')
def step_position_for_line_published(context, line_code):
    matches = [e for e in context.publisher.published if e.line_code == line_code]
    assert matches, f"Expected a published position for line {line_code!r}; got: {context.publisher.published}"


@then(r'the published position for vehicle "([^"]+)" has color "([^"]+)"')
def step_position_has_color(context, vehicle_id, color_hex):
    matches = [e for e in context.publisher.published if e.vehicle_id == vehicle_id]
    assert matches, f"Expected a published position for vehicle {vehicle_id!r}"
    assert matches[0].color_hex == color_hex, f"Expected color {color_hex!r}, got {matches[0].color_hex!r}"
