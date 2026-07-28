from __future__ import annotations

import math

from shared.logger import get_logger

from ...domain.conversation_state import ConversationState
from ...domain.line_query import parse_line_query
from ...domain.message_parser import IncomingMessage
from ...domain.repository import ConversationStateRepository

logger = get_logger(__name__)

# A stopped/very slow bus would otherwise imply an infinite straight-line ETA
# — floor the speed used for that fallback estimate.
MIN_ETA_SPEED_KMH = 15


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlon / 2) ** 2
    return r * 2 * math.asin(math.sqrt(a))


class HandleIncomingMessageHandler:
    """Keeps a per-chat memory of the last shared location and requested line
    (in whichever order they arrive) and, once both are known, replies with
    how far the nearest bus on that line is from the nearest stop to the
    user — reusing the bus-tracker api's live positions, GTFS stops, and the
    same OSRM street-network routing the dashboard's map uses."""

    def __init__(self, state_repo: ConversationStateRepository, bus_tracker, osrm, sender):
        self._state_repo = state_repo
        self._bus_tracker = bus_tracker
        self._osrm = osrm
        self._sender = sender

    async def handle(self, msg: IncomingMessage) -> None:
        if msg.from_me or not msg.remote_jid:
            return

        if msg.lat is not None and msg.lon is not None:
            self._state_repo.set_location(msg.remote_jid, msg.lat, msg.lon)

        line_query = parse_line_query(msg.text)
        if line_query is not None:
            self._state_repo.set_line(msg.remote_jid, line_query.mode, line_query.line_code)

        state = self._state_repo.get(msg.remote_jid)
        if not (state.has_location and state.has_line):
            return

        await self._reply_with_eta(state)

    async def _reply_with_eta(self, state: ConversationState) -> None:
        mode, line_code = state.mode, state.line_code
        try:
            self._bus_tracker.ensure_tracked_line(mode, line_code)
        except Exception as exc:
            logger.error(f"ensure_tracked_line failed for {mode}:{line_code}: {exc}", exc_info=True)

        positions = self._bus_tracker.find_latest_positions(mode, line_code)
        if not positions:
            await self._sender.send(
                state.remote_jid,
                f"🚌 Linha {line_code}: ainda não tenho ônibus em tempo real pra essa linha "
                "(acabei de começar a rastrear ela — tenta de novo em ~1 min).",
            )
            return

        nearest_bus = min(
            positions,
            key=lambda p: _haversine_km(state.lat, state.lon, p["latitude"], p["longitude"]),
        )

        stops = self._bus_tracker.find_stops(mode, line_code)
        nearest_stop = None
        if stops:
            nearest_stop = min(
                stops,
                key=lambda s: _haversine_km(state.lat, state.lon, s["lat"], s["lon"]),
            )

        if nearest_stop is not None:
            walk_minutes = await self._osrm.route_minutes(
                "foot", (state.lon, state.lat), (nearest_stop["lon"], nearest_stop["lat"]),
            )
            drive_minutes = await self._osrm.route_minutes(
                "car", (nearest_bus["longitude"], nearest_bus["latitude"]), (nearest_stop["lon"], nearest_stop["lat"]),
            )
            if walk_minutes is not None and drive_minutes is not None:
                await self._sender.send(
                    state.remote_jid,
                    f"🚌 Linha {line_code}\n"
                    f"Parada mais próxima: {nearest_stop.get('name') or 'sem nome'}\n"
                    f"A pé: ~{round(walk_minutes)} min\n"
                    f"Ônibus chega lá: ~{round(drive_minutes)} min",
                )
                return

        distance_km = _haversine_km(state.lat, state.lon, nearest_bus["latitude"], nearest_bus["longitude"])
        eta_minutes = (distance_km / max(nearest_bus["speed_kmh"], MIN_ETA_SPEED_KMH)) * 60
        await self._sender.send(
            state.remote_jid,
            f"🚌 Linha {line_code}\n"
            f"Ônibus mais próximo: {distance_km:.1f} km — ~{round(eta_minutes)} min "
            "(linha reta, sem rota por ruas)",
        )
