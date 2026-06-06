Feature: Mark chat as read

  Scenario: Unread count is zeroed
    Given an empty store
    And chat "5511@s.whatsapp.net" exists with unread count 3
    When I mark chat "5511@s.whatsapp.net" as read
    Then chat "5511@s.whatsapp.net" has unread count 0

  Scenario: Marking a non-existent chat is a no-op
    Given an empty store
    When I mark chat "9999@s.whatsapp.net" as read
    Then no chats are stored
