import asyncio
from datetime import datetime, timezone
from uuid import uuid4

from behave import given, then, use_step_matcher

from shared.events import BusPositionCaptured, EventMeta
from src.infrastructure.position_consumer import PositionConsumer

use_step_matcher("re")

PRODUCER = "test.bus-tracker-poller"


class InMemoryPositionRepository:
    """Mirrors PositionRepository's public surface and idempotency semantics
    (unique on vehicle_id+captured_at) without touching Postgres — same
    in-memory-fake-in-steps-file pattern used across every other service's
    BDD suite (e.g. domain-persister's InMemoryReadModelRepository)."""

    def __init__(self):
        self._rows: dict[tuple[str, str], dict] = {}

    def insert(self, line_code, vehicle_id, latitude, longitude, speed_kmh, captured_at) -> None:
        key = (vehicle_id, captured_at.isoformat())
        if key in self._rows:
            return
        self._rows[key] = {
            "line_code": line_code,
            "vehicle_id": vehicle_id,
            "latitude": latitude,
            "longitude": longitude,
            "speed_kmh": speed_kmh,
            "captured_at": captured_at.isoformat(),
        }

    def find_latest(self, line_code: str) -> list[dict]:
        latest_by_vehicle: dict[str, dict] = {}
        for row in sorted(self._rows.values(), key=lambda r: r["captured_at"], reverse=True):
            if row["line_code"] != line_code:
                continue
            latest_by_vehicle.setdefault(row["vehicle_id"], row)
        return list(latest_by_vehicle.values())

    def find_history(self, line_code: str, limit: int = 50, offset: int = 0) -> list[dict]:
        rows = [r for r in self._rows.values() if r["line_code"] == line_code]
        rows.sort(key=lambda r: r["captured_at"], reverse=True)
        return rows[offset:offset + limit]


def _ensure_setup(context):
    if not hasattr(context, "position_repo"):
        context.position_repo = InMemoryPositionRepository()
        context.sse_subs: dict = {}
        context.consumer = PositionConsumer(context.position_repo, context.sse_subs)


def _make_event(line_code: str, vehicle_id: str) -> BusPositionCaptured:
    now = datetime.now(timezone.utc)
    return BusPositionCaptured(
        meta=EventMeta(occurred_at=now, producer=PRODUCER, correlation_id=uuid4()),
        line_code=line_code,
        vehicle_id=vehicle_id,
        latitude=-22.9,
        longitude=-43.2,
        speed_kmh=30.0,
        captured_at=now,
    )


@given(r'a BusPositionCaptured event for line "([^"]+)" vehicle "([^"]+)" is projected')
def step_project_position(context, line_code, vehicle_id):
    _ensure_setup(context)
    context.last_event = _make_event(line_code, vehicle_id)
    raw = context.last_event.model_dump_json().encode()
    asyncio.run(context.consumer.project(raw))


@given("the same BusPositionCaptured event is projected again")
def step_project_same_event_again(context):
    raw = context.last_event.model_dump_json().encode()
    asyncio.run(context.consumer.project(raw))


@then(r'the latest positions for line "([^"]+)" include vehicle "([^"]+)"')
def step_latest_includes_vehicle(context, line_code, vehicle_id):
    positions = context.position_repo.find_latest(line_code)
    vehicles = {p["vehicle_id"] for p in positions}
    assert vehicle_id in vehicles, f"Expected vehicle {vehicle_id!r} in {vehicles}"


@then(r'the latest positions for line "([^"]+)" do not include vehicle "([^"]+)"')
def step_latest_excludes_vehicle(context, line_code, vehicle_id):
    positions = context.position_repo.find_latest(line_code)
    vehicles = {p["vehicle_id"] for p in positions}
    assert vehicle_id not in vehicles, f"Expected vehicle {vehicle_id!r} NOT in {vehicles}"


@then(r'the position history for line "([^"]+)" has (\d+) position')
def step_history_count(context, line_code, count):
    positions = context.position_repo.find_history(line_code, limit=1000)
    assert len(positions) == int(count), f"Expected {count} position(s), got {len(positions)}"
