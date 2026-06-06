Feature: Create card

  Background:
    Given an empty board repository
    And an empty card repository
    And a board named "Dev" exists

  Scenario: Create a card with valid data
    When I create a card with title "Task 1" status "todo" in the board
    Then the card is saved with title "Task 1" and status "todo"
    And a CardCreated event is published

  Scenario: Create a card with all statuses
    When I create a card with title "A" status "backlog" in the board
    Then the card is saved with title "A" and status "backlog"
    When I create a card with title "B" status "in_progress" in the board
    Then the card is saved with title "B" and status "in_progress"
    When I create a card with title "C" status "done" in the board
    Then the card is saved with title "C" and status "done"

  Scenario: Card title cannot be empty
    When I try to create a card with title "" status "todo" in the board
    Then a validation error contains "cannot be empty"

  Scenario: Invalid card status is rejected
    When I try to create a card with title "Task" status "invalid" in the board
    Then a validation error contains "invalid status"
