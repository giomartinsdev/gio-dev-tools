Feature: Send WhatsApp message

  Scenario: Send a valid message
    When I send message "Hello!" to number "5511999990000"
    Then the API is called with number "5511999990000" and text "Hello!"
    And the response is returned

  Scenario: Number cannot be empty
    When I try to send message "Hello" to number ""
    Then a validation error contains "number is required"

  Scenario: Message text cannot be empty
    When I try to send message "" to number "5511999990000"
    Then a validation error contains "message is required"

  Scenario: Number with only whitespace is rejected
    When I try to send message "Hi" to number "   "
    Then a validation error contains "number is required"
