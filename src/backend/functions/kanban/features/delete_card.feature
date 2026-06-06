Feature: Delete card

  Background:
    Given an empty board repository
    And an empty card repository
    And a board named "Dev" exists
    And a card with title "My Task" status "todo" exists in the board

  Scenario: Delete an existing card
    When I delete the card
    Then the card repository is empty
    And a CardDeleted event is published

  Scenario: Delete a non-existent card returns false
    When I delete card "non-existent-id"
    Then the deletion returns false
