Feature: Upsert chat from contacts or chats event

  Scenario: New chat is created with name
    Given an empty store
    When I upsert chat "5511@s.whatsapp.net" with name "Maria"
    Then chat "5511@s.whatsapp.net" has name "Maria"

  Scenario: Existing chat name is updated
    Given an empty store
    And chat "5511@s.whatsapp.net" exists with name "Unknown"
    When I upsert chat "5511@s.whatsapp.net" with name "Maria"
    Then chat "5511@s.whatsapp.net" has name "Maria"

  Scenario: Group JIDs are ignored
    Given an empty store
    When I upsert chat "123@g.us" with name "Group"
    Then no chats are stored

  Scenario: ChatUpdated event is published
    Given an empty store
    When I upsert chat "5511@s.whatsapp.net" with name "Maria"
    Then a ChatUpdated event was published with jid "5511@s.whatsapp.net"
