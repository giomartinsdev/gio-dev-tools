from src.domain.message import WhatsAppMessage
from src.infrastructure.evolution_client import EvolutionApiClient


class SendMessageUseCase:
    def __init__(self, client: EvolutionApiClient):
        self.client = client

    def execute(self, number: str, text: str) -> dict:
        message = WhatsAppMessage(number=number, text=text)
        return self.client.send_text(message)
