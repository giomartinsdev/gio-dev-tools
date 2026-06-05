from shared.request import Request
from shared.response import Response
from shared.logger import get_logger
from src.application.send_message_use_case import SendMessageUseCase
from src.infrastructure.evolution_client import EvolutionApiClient

logger = get_logger(__name__)


def main(request: Request) -> Response:
    body = request.body

    if not isinstance(body, dict):
        return Response(body={"error": "JSON body required"}, status_code=400)

    number = body.get("number")
    message = body.get("message")

    if not number or not message:
        return Response(
            body={"error": "number and message are required"},
            status_code=400,
        )

    try:
        client = EvolutionApiClient()
        use_case = SendMessageUseCase(client)
        result = use_case.execute(number=number, text=message)
        logger.info(f"message sent to {number}")
        return Response(body=result, status_code=200)
    except ValueError as e:
        return Response(body={"error": str(e)}, status_code=400)
    except Exception as e:
        logger.error(f"failed to send message: {e}")
        return Response(body={"error": "failed to send message"}, status_code=500)
