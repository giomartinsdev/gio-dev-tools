import os

from shared.logger import get_logger
from shared.request import Request
from shared.response import Response
from shared.transaction_manager import TransactionConfig, TransactionManager

from .application.commands.mark_chat_read import MarkChatReadCommand, MarkChatReadHandler
from .application.commands.process_incoming_message import ProcessIncomingMessageCommand, ProcessIncomingMessageHandler
from .application.commands.send_message import SendMessageCommand, SendMessageHandler
from .application.commands.update_message_status import UpdateMessageStatusCommand, UpdateMessageStatusHandler
from .application.commands.upsert_chat import UpsertChatCommand, UpsertChatHandler
from .application.queries.list_chats import ListChatsHandler, ListChatsQuery
from .application.queries.list_messages import ListMessagesHandler, ListMessagesQuery
from .domain.events import ChatUpdated, MessageReceived, MessageSent, MessageStatusUpdated
from .infrastructure.event_bus import get_event_bus
from .infrastructure.evolution_client import EvolutionApiClient
from .infrastructure.models import Base
from .infrastructure.postgres_repository import PostgresChatRepository, PostgresMessageRepository

logger = get_logger(__name__)

TransactionManager.configure(TransactionConfig(url=os.environ["DATABASE_URL"]))
Base.metadata.create_all(TransactionManager.get().engine)

_chat_repo = PostgresChatRepository()
_msg_repo = PostgresMessageRepository()
_evolution = EvolutionApiClient()
_bus = get_event_bus()

_bus.subscribe(MessageReceived, lambda e: logger.info(f"MessageReceived id={e.message_id} chat={e.chat_jid}"))
_bus.subscribe(MessageSent, lambda e: logger.info(f"MessageSent id={e.message_id} number={e.number}"))
_bus.subscribe(MessageStatusUpdated, lambda e: logger.info(f"MessageStatusUpdated id={e.message_id} status={e.status}"))
_bus.subscribe(ChatUpdated, lambda e: logger.info(f"ChatUpdated jid={e.jid} name={e.name}"))

_process_msg = ProcessIncomingMessageHandler(_chat_repo, _msg_repo, _bus)
_update_status = UpdateMessageStatusHandler(_msg_repo, _bus)
_upsert_chat = UpsertChatHandler(_chat_repo, _bus)
_send = SendMessageHandler(_evolution, _chat_repo, _msg_repo, _bus)
_mark_read = MarkChatReadHandler(_chat_repo)
_list_chats = ListChatsHandler(_chat_repo)
_list_messages = ListMessagesHandler(_msg_repo)


def main(request: Request) -> Response:
    try:
        body = request.body if isinstance(request.body, dict) else {}

        if request.method == "POST" and "event" in body:
            return _handle_webhook(body)

        if request.method == "GET":
            action = request.query.get("action", "")
            if action == "chats":
                return Response(body=_list_chats.handle(ListChatsQuery()), status_code=200)
            if action == "messages":
                jid = str(request.query.get("jid", ""))
                return Response(body=_list_messages.handle(ListMessagesQuery(jid=jid)), status_code=200)
            return Response(body={"error": "unknown action"}, status_code=400)

        if request.method == "POST":
            action = body.get("action", "")
            if action == "read":
                jid = str(body.get("jid", ""))
                if not jid:
                    return Response(body={"error": "jid is required"}, status_code=400)
                _mark_read.handle(MarkChatReadCommand(jid=jid))
                return Response(body={"ok": True}, status_code=200)
            result = _send.handle(SendMessageCommand(
                number=str(body.get("number", "")),
                text=str(body.get("message", "")),
            ))
            return Response(body=result, status_code=200)

        return Response(body={"error": "method not allowed"}, status_code=405)

    except ValueError as e:
        return Response(body={"error": str(e)}, status_code=400)
    except Exception as e:
        logger.error(f"unhandled error: {e}", exc_info=True)
        return Response(body={"error": "internal server error"}, status_code=500)


def _handle_webhook(body: dict) -> Response:
    event = body.get("event", "")
    data = body.get("data", {})
    try:
        if event == "MESSAGES_UPSERT":
            for msg in (data if isinstance(data, list) else [data]):
                key = msg.get("key", {})
                _process_msg.handle(ProcessIncomingMessageCommand(
                    jid=key.get("remoteJid", ""),
                    from_me=bool(key.get("fromMe", False)),
                    msg_id=key.get("id", ""),
                    message_payload=msg.get("message", {}),
                    timestamp_unix=float(msg.get("messageTimestamp") or 0),
                    status_raw=str(msg.get("status", "PENDING")),
                    push_name=msg.get("pushName"),
                ))
        elif event == "MESSAGES_UPDATE":
            if isinstance(data, list):
                for item in data:
                    msg_id = (item.get("key") or {}).get("id", "")
                    raw = (item.get("update") or {}).get("status", "")
                    if msg_id and raw:
                        _update_status.handle(UpdateMessageStatusCommand(msg_id=msg_id, status_raw=raw))
        elif event in ("CHATS_UPSERT", "CONTACTS_UPSERT"):
            if isinstance(data, list):
                for item in data:
                    jid = item.get("id", "")
                    name = item.get("name") or item.get("pushName")
                    if jid:
                        _upsert_chat.handle(UpsertChatCommand(jid=jid, name=name))
    except Exception as e:
        logger.error(f"webhook error for {event}: {e}", exc_info=True)
    return Response(body={"ok": True}, status_code=200)
