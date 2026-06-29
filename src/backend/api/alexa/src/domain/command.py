from __future__ import annotations
from dataclasses import dataclass


@dataclass
class AlexaCommand:
    text: str
    device_name: str | None = None

    def validate(self) -> None:
        if not self.text.strip():
            raise ValueError("command cannot be empty")
