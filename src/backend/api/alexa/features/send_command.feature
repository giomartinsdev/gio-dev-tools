Feature: Send Alexa command

  Scenario: Send a valid text command
    Given an Alexa client with device "Echo Pop"
    When I send the command "play lofi music"
    Then the command is dispatched to "Echo Pop"
    And the result has sent equal to true

  Scenario: Empty command is rejected
    Given an Alexa client with device "Echo Pop"
    When I try to send the command ""
    Then I get a ValueError "command cannot be empty"

  Scenario: Whitespace-only command is rejected
    Given an Alexa client with device "Echo Pop"
    When I try to send the command "   "
    Then I get a ValueError "command cannot be empty"
