import asyncio
import uuid
from datetime import datetime, timezone

from behave import given, then, use_step_matcher, when

from shared.transaction_manager import TransactionManager
from src.application.commands.poll_positions import PollPositionsCommand, PollPositionsHandler
from src.infrastructure.tracked_lines_read_repository import TrackedLineModel, TrackedLinesReadRepository

use_step_matcher("re")


class FakeRioGpsClient:
    def __init__(self, rows: list[dict]):
        self._rows = rows

    def fetch_positions(self, data_inicial, data_final) -> list[dict]:
        return self._rows


class FakePublisher:
    def __init__(self):
        self.published = []

    async def publish_domain_event(self, event) -> None:
        self.published.append(event)


def _insert_line(line_code: str, active: bool) -> None:
    now = datetime.now(timezone.utc)
    with TransactionManager.get().session() as s:
        s.add(TrackedLineModel(
            id=str(uuid.uuid4()),
            line_code=line_code,
            label=None,
            active=active,
            created_at=now,
            updated_at=now,
        ))


def _setup(context):
    context.rows = []
    context.publisher = FakePublisher()
    context.tracked_lines = TrackedLinesReadRepository()


@given("no tracked lines exist")
def step_no_lines(context):
    _setup(context)


@given(r'tracked line "([^"]+)" is active')
def step_line_active(context, line_code):
    if not hasattr(context, "publisher"):
        _setup(context)
    _insert_line(line_code, active=True)


@given(r'tracked line "([^"]+)" is inactive')
def step_line_inactive(context, line_code):
    if not hasattr(context, "publisher"):
        _setup(context)
    _insert_line(line_code, active=False)


def _sppo_row(line_code: str, ordem: str) -> dict:
    return {
        "ordem": ordem,
        "latitude": "-22,90434",
        "longitude": "-43,2863",
        "datahora": str(int(datetime.now(timezone.utc).timestamp() * 1000)),
        "velocidade": "30",
        "linha": line_code,
    }


@given(r'the SPPO feed returns positions for lines "([^"]+)", "([^"]+)" and "([^"]+)"')
def step_feed_three_lines(context, line_a, line_b, line_c):
    context.rows = [
        _sppo_row(line_a, "A1"),
        _sppo_row(line_b, "B1"),
        _sppo_row(line_c, "C1"),
    ]


@given(r'the SPPO feed returns positions for lines "([^"]+)"')
def step_feed_one_line(context, line_code):
    context.rows = [_sppo_row(line_code, "A1")]


@given(r'the SPPO feed returns a malformed row for line "([^"]+)"')
def step_feed_malformed(context, line_code):
    context.rows = [{"linha": line_code, "ordem": "A1"}]  # missing latitude/longitude/datahora


@when("positions are polled")
def step_poll(context):
    handler = PollPositionsHandler(
        FakeRioGpsClient(context.rows), context.tracked_lines, context.publisher,
    )
    context.published_count = asyncio.run(handler.handle(PollPositionsCommand()))


@then(r"(\d+) positions? (?:is|are) published")
def step_count_published(context, count):
    assert context.published_count == int(count), \
        f"Expected {count} published, got {context.published_count}"


@then(r'a position for line "([^"]+)" is published')
def step_position_for_line_published(context, line_code):
    matches = [e for e in context.publisher.published if e.line_code == line_code]
    assert matches, f"Expected a published position for line {line_code!r}; got: {context.publisher.published}"
