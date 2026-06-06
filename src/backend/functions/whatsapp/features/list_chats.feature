Feature: List chats query

  Scenario: Returns all chats as dicts
    Given an empty store
    And chat "5511@s.whatsapp.net" exists with name "Alice"
    And chat "5522@s.whatsapp.net" exists with name "Bob"
    When I list chats
    Then the result contains 2 chats
    And the result includes jid "5511@s.whatsapp.net"
    And the result includes jid "5522@s.whatsapp.net"

  Scenario: Returns empty list when no chats
    Given an empty store
    When I list chats
    Then the result contains 0 chats
