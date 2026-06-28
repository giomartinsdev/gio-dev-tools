Feature: Create board

  Scenario: Create a board with a valid name
    Given an empty board repository
    When I create a board named "Sprint 1"
    Then the board is saved with name "Sprint 1"
    And a BoardCreated event is published

  Scenario: Board name cannot be empty
    Given an empty board repository
    When I try to create a board named ""
    Then a validation error contains "cannot be empty"

  Scenario: Board name is trimmed
    Given an empty board repository
    When I create a board named "  My Board  "
    Then the board is saved with name "My Board"
