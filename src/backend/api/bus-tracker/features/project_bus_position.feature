Feature: Project bus position events

  Scenario: A captured position is persisted
    Given a BusPositionCaptured event for line "483" vehicle "B12345" is projected
    Then the latest positions for line "483" include vehicle "B12345"

  Scenario: The same position is never duplicated
    Given a BusPositionCaptured event for line "483" vehicle "B12345" is projected
    And the same BusPositionCaptured event is projected again
    Then the position history for line "483" has 1 position

  Scenario: Positions are filtered by line
    Given a BusPositionCaptured event for line "483" vehicle "B12345" is projected
    And a BusPositionCaptured event for line "606" vehicle "C99999" is projected
    Then the latest positions for line "483" include vehicle "B12345"
    And the latest positions for line "483" do not include vehicle "C99999"

  Scenario: SPPO and BRT positions for the same line code never mix
    Given a BusPositionCaptured event for mode "sppo" line "22" vehicle "B12345" is projected
    And a BusPositionCaptured event for mode "brt" line "22" vehicle "901008" is projected
    Then the latest positions for mode "sppo" line "22" include vehicle "B12345"
    And the latest positions for mode "sppo" line "22" do not include vehicle "901008"
    And the latest positions for mode "brt" line "22" include vehicle "901008"
    And the latest positions for mode "brt" line "22" do not include vehicle "B12345"

  Scenario: A position's operator color is persisted when available
    Given a BusPositionCaptured event for line "483" vehicle "B12345" with color "#9E652E" is projected
    Then the latest position for vehicle "B12345" has color "#9E652E"
