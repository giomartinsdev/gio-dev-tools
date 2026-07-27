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
