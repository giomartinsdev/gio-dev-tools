Feature: Poll bus positions

  Scenario: Only positions for active tracked SPPO lines are published
    Given tracked line "483" mode "sppo" is active
    And tracked line "606" mode "sppo" is active
    And the SPPO feed returns positions for lines "483", "606" and "999"
    When positions are polled
    Then 2 positions are published
    And a position for line "483" is published
    And a position for line "606" is published

  Scenario: Inactive lines are not polled
    Given tracked line "483" mode "sppo" is inactive
    And the SPPO feed returns positions for lines "483"
    When positions are polled
    Then 0 positions are published

  Scenario: No tracked lines means no feed call is needed
    Given no tracked lines exist
    And the SPPO feed returns positions for lines "483"
    When positions are polled
    Then 0 positions are published

  Scenario: Malformed SPPO rows are skipped
    Given tracked line "483" mode "sppo" is active
    And the SPPO feed returns a malformed row for line "483"
    When positions are polled
    Then 0 positions are published

  Scenario: BRT positions are polled independently of SPPO
    Given tracked line "22" mode "brt" is active
    And the BRT feed returns positions for lines "22" and "50"
    When positions are polled
    Then 1 position is published
    And a position for line "22" is published

  Scenario: SPPO and BRT are polled together when both have active lines
    Given tracked line "483" mode "sppo" is active
    And tracked line "22" mode "brt" is active
    And the SPPO feed returns positions for lines "483"
    And the BRT feed returns positions for lines "22" and "50"
    When positions are polled
    Then 2 positions are published

  Scenario: Vehicle colors are attached when available
    Given tracked line "483" mode "sppo" is active
    And the SPPO feed returns positions for lines "483"
    And the vehicle color feed maps vehicle "A1" to color "#ABCDEF"
    When positions are polled
    Then the published position for vehicle "A1" has color "#ABCDEF"
