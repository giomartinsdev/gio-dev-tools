Feature: Poll bus positions

  Scenario: Only positions for active tracked lines are published
    Given tracked line "483" is active
    And tracked line "606" is active
    And the SPPO feed returns positions for lines "483", "606" and "999"
    When positions are polled
    Then 2 positions are published
    And a position for line "483" is published
    And a position for line "606" is published

  Scenario: Inactive lines are not polled
    Given tracked line "483" is inactive
    And the SPPO feed returns positions for lines "483"
    When positions are polled
    Then 0 positions are published

  Scenario: No tracked lines means no feed call is needed
    Given no tracked lines exist
    And the SPPO feed returns positions for lines "483"
    When positions are polled
    Then 0 positions are published

  Scenario: Malformed rows are skipped
    Given tracked line "483" is active
    And the SPPO feed returns a malformed row for line "483"
    When positions are polled
    Then 0 positions are published
