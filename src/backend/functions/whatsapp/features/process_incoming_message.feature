Feature: Process incoming WhatsApp message

  Scenario: Incoming message creates chat with unread count 1
    Given an empty store
    When I process an incoming message from "5511@s.whatsapp.net" id "m1" text "Oi" fromMe false
    Then chat "5511@s.whatsapp.net" has unread count 1
    And message "m1" exists with text "Oi" and from_me false

  Scenario: Outgoing message does not increment unread
    Given an empty store
    When I process an incoming message from "5511@s.whatsapp.net" id "m1" text "Oi" fromMe true
    Then chat "5511@s.whatsapp.net" has unread count 0
    And message "m1" exists with text "Oi" and from_me true

  Scenario: Push name is stored on the chat
    Given an empty store
    When I process an incoming message from "5511@s.whatsapp.net" id "m1" text "Oi" fromMe false with push name "João"
    Then chat "5511@s.whatsapp.net" has name "João"

  Scenario: Group messages are ignored
    Given an empty store
    When I process an incoming message from "123@g.us" id "m1" text "hello" fromMe false
    Then no chats are stored

  Scenario: status@broadcast messages are ignored
    Given an empty store
    When I process an incoming message from "status@broadcast" id "m1" text "status" fromMe false
    Then no chats are stored

  Scenario: MessageReceived event is published for incoming messages
    Given an empty store
    When I process an incoming message from "5511@s.whatsapp.net" id "m1" text "Oi" fromMe false
    Then a MessageReceived event was published with message_id "m1"

  Scenario: No event is published for outgoing messages
    Given an empty store
    When I process an incoming message from "5511@s.whatsapp.net" id "m1" text "Oi" fromMe true
    Then no MessageReceived event was published
