Feature: Send WhatsApp message

  Scenario: Message is sent and persisted
    Given an empty store
    When I send message "Hello!" to number "5511999990000"
    Then the gateway is called with number "5511999990000" and text "Hello!"
    And message "fake-msg-id" exists with text "Hello!" and from_me true
    And a MessageSent event was published with number "5511999990000"

  Scenario: Empty number raises validation error
    Given an empty store
    When I try to send message "Hello" to number ""
    Then a validation error contains "number is required"

  Scenario: Empty text raises validation error
    Given an empty store
    When I try to send message "" to number "5511999990000"
    Then a validation error contains "message is required"

  Scenario: Whitespace-only number raises validation error
    Given an empty store
    When I try to send message "Hi" to number "   "
    Then a validation error contains "number is required"
