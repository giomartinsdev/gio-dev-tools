import os

import httpx

from ..domain.repository import MessageGateway


class EvolutionApiClient(MessageGateway):
    def __init__(self):
        self.base_url = os.environ["EVOLUTION_URL"]
        self.api_key = os.environ["EVOLUTION_API_KEY"]
        self.instance = os.environ["EVOLUTION_INSTANCE_NAME"]

    def send_text(self, number: str, text: str) -> dict:
        response = httpx.post(
            f"{self.base_url}/message/sendText/{self.instance}",
            headers={"apikey": self.api_key, "Content-Type": "application/json"},
            json={"number": number, "text": text},
            timeout=30.0,
        )
        response.raise_for_status()
        return response.json()
