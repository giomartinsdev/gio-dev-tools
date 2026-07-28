Feature: Talk to the bus-tracker api over HTTP

  Scenario: A line that already exists is not recreated
    Given the bus-tracker api already tracks mode "sppo" line "483"
    When I ensure line "483" mode "sppo" is tracked
    Then no POST to /lines was made

  Scenario: A line that doesn't exist yet is created
    Given the bus-tracker api tracks no lines
    When I ensure line "483" mode "sppo" is tracked
    Then a POST to /lines was made for line "483" mode "sppo"

  Scenario: Latest positions are fetched
    Given the bus-tracker api returns positions [{"vehicle_id": "B1"}] for mode "sppo" line "483"
    When I fetch latest positions for mode "sppo" line "483"
    Then the positions result is [{"vehicle_id": "B1"}]

  Scenario: Stops are fetched
    Given the bus-tracker api returns stops [{"name": "Central"}] for mode "sppo" line "483"
    When I fetch stops for mode "sppo" line "483"
    Then the stops result is [{"name": "Central"}]
