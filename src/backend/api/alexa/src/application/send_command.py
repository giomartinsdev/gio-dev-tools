from __future__ import annotations
from ..domain.command import AlexaCommand
from ..domain.port import AlexaClientPort


class SendCommandHandler:
    def __init__(self, client: AlexaClientPort) -> None:
        self._client = client

    async def handle(self, text: str, device_name: str | None = None) -> dict:
        cmd = AlexaCommand(text=text, device_name=device_name)
        cmd.validate()
        await self._client.send_command(cmd)
        return {"sent": True, "text": cmd.text, "device": device_name}
