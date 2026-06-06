Feature: List messages query

  Scenario: Returns messages for the given chat
    Given an empty store
    And message "m1" for chat "5511@s.whatsapp.net" with text "Oi" exists
    And message "m2" for chat "5511@s.whatsapp.net" with text "Tudo bem?" exists
    When I list messages for chat "5511@s.whatsapp.net"
    Then the result contains 2 messages

  Scenario: Returns empty list for chat with no messages
    Given an empty store
    When I list messages for chat "5511@s.whatsapp.net"
    Then the result contains 0 messages

  Scenario: Does not return messages from other chats
    Given an empty store
    And message "m1" for chat "5511@s.whatsapp.net" with text "Oi" exists
    When I list messages for chat "9999@s.whatsapp.net"
    Then the result contains 0 messages
