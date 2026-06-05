import os
import httpx
from src.domain.message import WhatsAppMessage


class EvolutionApiClient:
    def __init__(self):
        self.base_url = os.environ["EVOLUTION_URL"]
        self.api_key = os.environ["EVOLUTION_API_KEY"]
        self.instance = os.environ["EVOLUTION_INSTANCE_NAME"]

    def send_text(self, message: WhatsAppMessage) -> dict:
        response = httpx.post(
            f"{self.base_url}/message/sendText/{self.instance}",
            headers={
                "apikey": self.api_key,
                "Content-Type": "application/json",
            },
            json={
                "number": message.number,
                "text": message.text,
            },
            timeout=30.0,
        )
        response.raise_for_status()
        return response.json()
