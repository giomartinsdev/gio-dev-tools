from datetime import datetime, timezone
from typing import Optional

from behave import given, then, use_step_matcher, when

from src.application.commands.mark_chat_read import MarkChatReadCommand, MarkChatReadHandler
from src.application.commands.process_incoming_message import ProcessIncomingMessageCommand, ProcessIncomingMessageHandler
from src.application.commands.send_message import SendMessageCommand, SendMessageHandler
from src.application.commands.update_message_status import UpdateMessageStatusCommand, UpdateMessageStatusHandler
from src.application.commands.upsert_chat import UpsertChatCommand, UpsertChatHandler
from src.application.queries.list_chats import ListChatsHandler, ListChatsQuery
from src.application.queries.list_messages import ListMessagesHandler, ListMessagesQuery
from src.domain.chat import Chat
from src.domain.events import DomainEvent
from src.domain.message import Message, MessageStatus
from src.domain.repository import ChatRepository, MessageGateway, MessageRepository
from src.infrastructure.event_bus import EventBus

use_step_matcher("re")

# ---------------------------------------------------------------------------
# In-memory implementations
# ---------------------------------------------------------------------------

class InMemoryChatRepository(ChatRepository):
    def __init__(self):
        self._store: dict[str, Chat] = {}

    def save(self, chat: Chat) -> None:
        self._store[chat.jid] = chat

    def find_by_jid(self, jid: str) -> Optional[Chat]:
        return self._store.get(jid)

    def find_all(self) -> list[Chat]:
        return sorted(
            self._store.values(),
            key=lambda c: c.last_message_at or datetime.min.replace(tzinfo=timezone.utc),
            reverse=True,
        )


class InMemoryMessageRepository(MessageRepository):
    def __init__(self):
        self._store: dict[str, Message] = {}

    def save(self, message: Message) -> None:
        if message.id in self._store:
            existing = self._store[message.id]
            if message.status != MessageStatus.PENDING:
                self._store[message.id] = existing.with_status(message.status)
        else:
            self._store[message.id] = message

    def find_by_id(self, msg_id: str) -> Optional[Message]:
        return self._store.get(msg_id)

    def find_by_chat(self, chat_jid: str, limit: int = 100) -> list[Message]:
        msgs = [m for m in self._store.values() if m.chat_jid == chat_jid]
        return sorted(msgs, key=lambda m: m.timestamp)[:limit]

    def update_status(self, msg_id: str, status: MessageStatus) -> None:
        if msg_id in self._store:
            self._store[msg_id] = self._store[msg_id].with_status(status)


class FakeMessageGateway(MessageGateway):
    def __init__(self):
        self.calls: list[dict] = []

    def send_text(self, number: str, text: str) -> dict:
        self.calls.append({"number": number, "text": text})
        return {
            "key": {"id": "fake-msg-id", "fromMe": True},
            "messageTimestamp": 1700000000,
            "status": "PENDING",
        }


class SpyEventBus(EventBus):
    def __init__(self):
        super().__init__()
        self.published: list[DomainEvent] = []

    def publish(self, event: DomainEvent) -> None:
        self.published.append(event)
        super().publish(event)


# ---------------------------------------------------------------------------
# Given
# ---------------------------------------------------------------------------

@given(r'an empty store')
def step_empty_store(context):
    context.chat_repo = InMemoryChatRepository()
    context.msg_repo = InMemoryMessageRepository()
    context.gateway = FakeMessageGateway()
    context.bus = SpyEventBus()
    context.result = None
    context.last_error = None


@given(r'chat "([^"]+)" exists with name "([^"]+)"')
def step_chat_with_name(context, jid, name):
    context.chat_repo.save(Chat.create(jid, name=name))


@given(r'chat "([^"]+)" exists with unread count (\d+)')
def step_chat_with_unread(context, jid, count):
    chat = Chat.create(jid)
    chat = chat.model_copy(update={"unread_count": int(count)})
    context.chat_repo.save(chat)


@given(r'message "([^"]+)" exists with status "([^"]+)"')
def step_message_with_status(context, msg_id, status):
    context.msg_repo._store[msg_id] = Message.create(
        msg_id=msg_id,
        chat_jid="5511@s.whatsapp.net",
        from_me=True,
        text="hi",
        timestamp=datetime.now(tz=timezone.utc),
        status=MessageStatus(status),
    )


@given(r'message "([^"]+)" for chat "([^"]+)" with text "([^"]+)" exists')
def step_message_for_chat(context, msg_id, jid, text):
    context.msg_repo._store[msg_id] = Message.create(
        msg_id=msg_id,
        chat_jid=jid,
        from_me=False,
        text=text,
        timestamp=datetime.now(tz=timezone.utc),
    )


# ---------------------------------------------------------------------------
# When — process_incoming_message
# ---------------------------------------------------------------------------

@when(r'I process an incoming message from "([^"]+)" id "([^"]+)" text "([^"]*)" fromMe (true|false)')
def step_process_message(context, jid, msg_id, text, from_me_str):
    handler = ProcessIncomingMessageHandler(context.chat_repo, context.msg_repo, context.bus)
    handler.handle(ProcessIncomingMessageCommand(
        jid=jid, from_me=(from_me_str == "true"), msg_id=msg_id,
        message_payload={"conversation": text}, timestamp_unix=1700000000,
    ))


@when(r'I process an incoming message from "([^"]+)" id "([^"]+)" text "([^"]*)" fromMe (true|false) with push name "([^"]+)"')
def step_process_message_with_name(context, jid, msg_id, text, from_me_str, push_name):
    handler = ProcessIncomingMessageHandler(context.chat_repo, context.msg_repo, context.bus)
    handler.handle(ProcessIncomingMessageCommand(
        jid=jid, from_me=(from_me_str == "true"), msg_id=msg_id,
        message_payload={"conversation": text}, timestamp_unix=1700000000,
        push_name=push_name,
    ))


# ---------------------------------------------------------------------------
# When — update_message_status
# ---------------------------------------------------------------------------

@when(r'I update message "([^"]+)" status to "([^"]+)"')
def step_update_status(context, msg_id, status_raw):
    handler = UpdateMessageStatusHandler(context.msg_repo, context.bus)
    handler.handle(UpdateMessageStatusCommand(msg_id=msg_id, status_raw=status_raw))


# ---------------------------------------------------------------------------
# When — upsert_chat
# ---------------------------------------------------------------------------

@when(r'I upsert chat "([^"]+)" with name "([^"]+)"')
def step_upsert_chat(context, jid, name):
    handler = UpsertChatHandler(context.chat_repo, context.bus)
    handler.handle(UpsertChatCommand(jid=jid, name=name))


# ---------------------------------------------------------------------------
# When — send_message
# ---------------------------------------------------------------------------

@when(r'I send message "([^"]*)" to number "([^"]*)"')
def step_send(context, text, number):
    handler = SendMessageHandler(context.gateway, context.chat_repo, context.msg_repo, context.bus)
    context.result = handler.handle(SendMessageCommand(number=number, text=text))


@when(r'I try to send message "([^"]*)" to number "([^"]*)"')
def step_try_send(context, text, number):
    handler = SendMessageHandler(context.gateway, context.chat_repo, context.msg_repo, context.bus)
    try:
        handler.handle(SendMessageCommand(number=number, text=text))
        context.last_error = None
    except Exception as e:
        context.last_error = e


# ---------------------------------------------------------------------------
# When — mark_chat_read
# ---------------------------------------------------------------------------

@when(r'I mark chat "([^"]+)" as read')
def step_mark_read(context, jid):
    handler = MarkChatReadHandler(context.chat_repo)
    handler.handle(MarkChatReadCommand(jid=jid))


# ---------------------------------------------------------------------------
# When — queries
# ---------------------------------------------------------------------------

@when(r'I list chats')
def step_list_chats(context):
    context.result = ListChatsHandler(context.chat_repo).handle(ListChatsQuery())


@when(r'I list messages for chat "([^"]+)"')
def step_list_messages(context, jid):
    context.result = ListMessagesHandler(context.msg_repo).handle(ListMessagesQuery(jid=jid))


# ---------------------------------------------------------------------------
# Then — chat assertions
# ---------------------------------------------------------------------------

@then(r'chat "([^"]+)" has unread count (\d+)')
def step_unread_count(context, jid, count):
    chat = context.chat_repo._store.get(jid)
    assert chat is not None, f"Chat {jid} not found"
    assert chat.unread_count == int(count), f"Expected unread={count}, got {chat.unread_count}"


@then(r'chat "([^"]+)" has name "([^"]+)"')
def step_chat_name(context, jid, name):
    chat = context.chat_repo._store.get(jid)
    assert chat is not None, f"Chat {jid} not found"
    assert chat.name == name, f"Expected name '{name}', got '{chat.name}'"


@then(r'no chats are stored')
def step_no_chats(context):
    assert not context.chat_repo._store, f"Expected no chats, found: {list(context.chat_repo._store.keys())}"


# ---------------------------------------------------------------------------
# Then — message assertions
# ---------------------------------------------------------------------------

@then(r'message "([^"]+)" exists with text "([^"]+)" and from_me (true|false)')
def step_message_exists(context, msg_id, text, from_me_str):
    msg = context.msg_repo._store.get(msg_id)
    assert msg is not None, f"Message {msg_id} not found"
    assert msg.text == text, f"Expected text '{text}', got '{msg.text}'"
    assert msg.from_me is (from_me_str == "true"), f"Expected from_me={from_me_str}"


@then(r'message "([^"]+)" has status "([^"]+)"')
def step_message_status(context, msg_id, status):
    msg = context.msg_repo._store.get(msg_id)
    assert msg is not None, f"Message {msg_id} not found"
    assert msg.status.value == status, f"Expected status '{status}', got '{msg.status.value}'"


# ---------------------------------------------------------------------------
# Then — send_message assertions
# ---------------------------------------------------------------------------

@then(r'the gateway is called with number "([^"]+)" and text "([^"]+)"')
def step_gateway_called(context, number, text):
    assert context.gateway.calls, "Expected gateway to be called"
    call = context.gateway.calls[-1]
    assert call["number"] == number
    assert call["text"] == text


@then(r'a validation error contains "([^"]+)"')
def step_validation_error(context, message):
    assert context.last_error is not None, "Expected a validation error but none was raised"
    assert message in str(context.last_error), f"Expected '{message}' in: {context.last_error}"


# ---------------------------------------------------------------------------
# Then — event assertions
# ---------------------------------------------------------------------------

@then(r'a MessageReceived event was published with message_id "([^"]+)"')
def step_message_received_event(context, msg_id):
    from src.domain.events import MessageReceived
    events = [e for e in context.bus.published if isinstance(e, MessageReceived)]
    assert events, "No MessageReceived event published"
    assert events[0].message_id == msg_id


@then(r'no MessageReceived event was published')
def step_no_message_received_event(context):
    from src.domain.events import MessageReceived
    events = [e for e in context.bus.published if isinstance(e, MessageReceived)]
    assert not events, f"Expected no MessageReceived event, found {len(events)}"


@then(r'a MessageStatusUpdated event was published with message_id "([^"]+)" and status "([^"]+)"')
def step_status_updated_event(context, msg_id, status):
    from src.domain.events import MessageStatusUpdated
    events = [e for e in context.bus.published if isinstance(e, MessageStatusUpdated)]
    assert events, "No MessageStatusUpdated event published"
    assert events[0].message_id == msg_id
    assert events[0].status == status


@then(r'a ChatUpdated event was published with jid "([^"]+)"')
def step_chat_updated_event(context, jid):
    from src.domain.events import ChatUpdated
    events = [e for e in context.bus.published if isinstance(e, ChatUpdated)]
    assert events, "No ChatUpdated event published"
    assert events[0].jid == jid


@then(r'a MessageSent event was published with number "([^"]+)"')
def step_message_sent_event(context, number):
    from src.domain.events import MessageSent
    events = [e for e in context.bus.published if isinstance(e, MessageSent)]
    assert events, "No MessageSent event published"
    assert events[0].number == number


# ---------------------------------------------------------------------------
# Then — query result assertions
# ---------------------------------------------------------------------------

@then(r'the result contains (\d+) chats')
def step_result_chats_count(context, count):
    assert len(context.result) == int(count), f"Expected {count} chats, got {len(context.result)}"


@then(r'the result includes jid "([^"]+)"')
def step_result_includes_jid(context, jid):
    jids = [c["jid"] for c in context.result]
    assert jid in jids, f"Expected jid '{jid}' in {jids}"


@then(r'the result contains (\d+) messages')
def step_result_messages_count(context, count):
    assert len(context.result) == int(count), f"Expected {count} messages, got {len(context.result)}"
