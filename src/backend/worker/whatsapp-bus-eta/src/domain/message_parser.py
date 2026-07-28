from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class IncomingMessage:
    remote_jid: Optional[str]
    from_me: bool
    text: Optional[str]
    lat: Optional[float]
    lon: Optional[float]


def parse_evolution_payload(payload: dict) -> IncomingMessage:
    """Evolution API (Baileys) `messages.upsert` event shape — the same
    `data.key` / `data.message` structure already relied on by the whatsapp
    worker and api services for persistence and chat listing."""
    data = payload.get("data") or {}
    key = data.get("key") or {}
    remote_jid = key.get("remoteJid") or data.get("remoteJid")
    from_me = bool(key.get("fromMe"))

    message = data.get("message") or {}
    text = message.get("conversation") or (message.get("extendedTextMessage") or {}).get("text")

    lat = lon = None
    location = message.get("locationMessage")
    if isinstance(location, dict):
        try:
            lat = float(location["degreesLatitude"])
            lon = float(location["degreesLongitude"])
        except (KeyError, TypeError, ValueError):
            lat = lon = None

    return IncomingMessage(remote_jid=remote_jid, from_me=from_me, text=text, lat=lat, lon=lon)
