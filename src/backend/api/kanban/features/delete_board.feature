Feature: Delete board

  Background:
    Given an empty board repository
    And a board named "My Board" exists

  Scenario: Delete an existing board
    When I delete the board
    Then the board repository is empty
    And a BoardDeleted event is published

  Scenario: Delete a non-existent board returns false
    When I delete board "non-existent-id"
    Then the deletion returns false
