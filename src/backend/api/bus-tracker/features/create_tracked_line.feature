Feature: Register a tracked bus line

  Scenario: Register a new line
    Given an empty tracked line repository
    When I create a tracked line with code "483" label "Rocinha - Leblon"
    Then the tracked line is saved with code "483" and label "Rocinha - Leblon"
    And a TrackedLineCreated event is published

  Scenario: Line code cannot be empty
    Given an empty tracked line repository
    When I try to create a tracked line with code ""
    Then a validation error contains "line_code is required"

  Scenario: A line defaults to SPPO mode
    Given an empty tracked line repository
    When I create a tracked line with code "483" label "Rocinha - Leblon"
    Then the tracked line has mode "sppo"

  Scenario: A line can be registered as BRT
    Given an empty tracked line repository
    When I create a tracked line with code "22" mode "brt"
    Then the tracked line has mode "brt"

  Scenario: An invalid mode is rejected
    Given an empty tracked line repository
    When I try to create a tracked line with code "22" mode "trem"
    Then a validation error contains "Invalid mode"

  Scenario: Update an existing line
    Given a tracked line with code "483" exists
    When I update the line to code "483" label "Rocinha" active "false"
    Then the tracked line is saved with code "483" and label "Rocinha"
    And the tracked line is inactive

  Scenario: Updating a missing line returns nothing
    Given an empty tracked line repository
    When I try to update line "missing-id" to code "483"
    Then no line is returned

  Scenario: Delete an existing line
    Given a tracked line with code "483" exists
    When I delete the line
    Then the tracked line repository is empty

  Scenario: Deleting a missing line returns false
    Given an empty tracked line repository
    When I try to delete line "missing-id"
    Then the deletion returns false
