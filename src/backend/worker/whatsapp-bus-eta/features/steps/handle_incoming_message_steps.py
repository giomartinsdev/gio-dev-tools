import asyncio

from behave import given, then, use_step_matcher, when

from src.application.commands.handle_incoming_message import HandleIncomingMessageHandler
from src.domain.conversation_state import ConversationState
from src.domain.message_parser import IncomingMessage
from src.domain.repository import ConversationStateRepository

use_step_matcher("re")

REMOTE_JID = "5511999@s.whatsapp.net"


class FakeStateRepository(ConversationStateRepository):
    def __init__(self):
        self._states: dict[str, ConversationState] = {}

    def get(self, remote_jid: str) -> ConversationState:
        return self._states.get(remote_jid) or ConversationState(remote_jid=remote_jid)

    def set_location(self, remote_jid: str, lat: float, lon: float) -> None:
        state = self.get(remote_jid)
        state.lat, state.lon = lat, lon
        self._states[remote_jid] = state

    def set_line(self, remote_jid: str, mode: str, line_code: str) -> None:
        state = self.get(remote_jid)
        state.mode, state.line_code = mode, line_code
        self._states[remote_jid] = state


class FakeBusTracker:
    def __init__(self):
        self.positions: dict[tuple[str, str], list[dict]] = {}
        self.stops: dict[tuple[str, str], list[dict]] = {}
        self.ensured: list[tuple[str, str]] = []

    def ensure_tracked_line(self, mode: str, line_code: str) -> None:
        self.ensured.append((mode, line_code))

    def find_latest_positions(self, mode: str, line_code: str) -> list[dict]:
        return self.positions.get((mode, line_code), [])

    def find_stops(self, mode: str, line_code: str) -> list[dict]:
        return self.stops.get((mode, line_code), [])


class FakeOsrm:
    def __init__(self):
        self.walk_minutes = None
        self.drive_minutes = None

    async def route_minutes(self, profile, from_lonlat, to_lonlat):
        return self.walk_minutes if profile == "foot" else self.drive_minutes


class FakeSender:
    def __init__(self):
        self.sent: list[tuple[str, str]] = []

    async def send(self, number: str, text: str) -> None:
        self.sent.append((number, text))


def _setup(context):
    context.state_repo = FakeStateRepository()
    context.bus_tracker = FakeBusTracker()
    context.osrm = FakeOsrm()
    context.sender = FakeSender()
    context.handler = HandleIncomingMessageHandler(context.state_repo, context.bus_tracker, context.osrm, context.sender)


@given("no conversation state exists")
def step_no_state(context):
    _setup(context)


@given(r'the bus tracker has a live bus for mode "([^"]+)" line "([^"]+)" at (-?[\d.]+) (-?[\d.]+) speed (\d+)')
def step_add_bus(context, mode, line_code, lat, lon, speed):
    context.bus_tracker.positions[(mode, line_code)] = [{
        "latitude": float(lat), "longitude": float(lon), "speed_kmh": float(speed),
    }]


@given(r'the bus tracker has no live buses for mode "([^"]+)" line "([^"]+)"')
def step_no_buses(context, mode, line_code):
    context.bus_tracker.positions[(mode, line_code)] = []


@given(r'the bus tracker has a stop for mode "([^"]+)" line "([^"]+)" named "([^"]+)" at (-?[\d.]+) (-?[\d.]+)')
def step_add_stop(context, mode, line_code, name, lat, lon):
    context.bus_tracker.stops.setdefault((mode, line_code), []).append({
        "name": name, "lat": float(lat), "lon": float(lon),
    })


@given(r'no stops are registered for mode "([^"]+)" line "([^"]+)"')
def step_no_stops(context, mode, line_code):
    context.bus_tracker.stops[(mode, line_code)] = []


@given(r"OSRM reports a walk of (\d+) minutes and a drive of (\d+) minutes")
def step_osrm(context, walk, drive):
    context.osrm.walk_minutes = float(walk)
    context.osrm.drive_minutes = float(drive)


def _handle(context, msg: IncomingMessage) -> None:
    asyncio.run(context.handler.handle(msg))


@when(r"the user shares their location (-?[\d.]+) (-?[\d.]+)")
def step_share_location(context, lat, lon):
    _handle(context, IncomingMessage(remote_jid=REMOTE_JID, from_me=False, text=None, lat=float(lat), lon=float(lon)))


@when(r'the user sends the text "([^"]+)"')
def step_send_text(context, text):
    _handle(context, IncomingMessage(remote_jid=REMOTE_JID, from_me=False, text=text, lat=None, lon=None))


@when(r'a message from me with text "([^"]+)" arrives')
def step_message_from_me(context, text):
    _handle(context, IncomingMessage(remote_jid=REMOTE_JID, from_me=True, text=text, lat=None, lon=None))


@then("no reply is sent yet")
def step_no_reply(context):
    assert context.sender.sent == [], f"Expected no replies, got: {context.sender.sent}"


@then(r'a reply is sent containing "([^"]+)"')
def step_reply_contains(context, fragment):
    assert any(fragment in text for _, text in context.sender.sent), \
        f"Expected a reply containing {fragment!r}; got: {context.sender.sent}"
