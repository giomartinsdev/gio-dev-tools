Feature: Update card

  Background:
    Given an empty board repository
    And an empty card repository
    And a board named "Dev" exists
    And a card with title "Old Title" status "todo" exists in the board

  Scenario: Update a card successfully
    When I update the card with title "New Title" status "in_progress"
    Then the card has title "New Title" and status "in_progress"
    And a CardUpdated event is published

  Scenario: Update card with empty title is rejected
    When I try to update the card with title "" status "todo"
    Then a validation error contains "cannot be empty"

  Scenario: Update card with invalid status is rejected
    When I try to update the card with title "Title" status "flying"
    Then a validation error contains "invalid status"

  Scenario: Update non-existent card returns nothing
    When I update card "non-existent-id" with title "X" status "todo"
    Then no update is performed
