from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class ConversationState:
    remote_jid: str
    lat: Optional[float] = None
    lon: Optional[float] = None
    mode: Optional[str] = None
    line_code: Optional[str] = None

    @property
    def has_location(self) -> bool:
        return self.lat is not None and self.lon is not None

    @property
    def has_line(self) -> bool:
        return self.mode is not None and self.line_code is not None
